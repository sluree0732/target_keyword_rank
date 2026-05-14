import json
import re


_KEYWORD_RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'results': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'index': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'keywords': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                },
                'required': ['index', 'keywords'],
            },
        },
    },
    'required': ['results'],
}


def extract_keywords_batch(
    titles: list,
    grade: int,
    count: int,
    api_key: str,
) -> dict:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    # 등급 1(세부 롱테일)은 다양한 조합 생성을 위해 temperature를 높임
    temperature_by_grade = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.15, 5: 0.1}
    temperature = temperature_by_grade.get(grade, 0.2)

    response = model.generate_content(
        _build_prompt(titles, grade, count),
        generation_config={
            'response_mime_type': 'application/json',
            'response_schema': _KEYWORD_RESPONSE_SCHEMA,
            'temperature': temperature,
            'candidate_count': 1,
        },
    )

    data = json.loads(response.text)
    return _normalize_keyword_results(data, titles, count)


def _build_prompt(titles: list, grade: int, count: int) -> str:
    titles_text = '\n'.join(f'{i + 1}. {title}' for i, title in enumerate(titles))

    detail_guide = {
        1: '가장 구체적인 롱테일 키워드. 세부 장소·브랜드명·매장명·구체 특징을 모두 포함',
        2: '구체적인 키워드. 브랜드명·매장명 포함 가능. 게시글과의 정확한 일치 우선',
        3: '중간 키워드. 장소/대상+특징+카테고리 조합. 브랜드명·매장명 제외',
        4: '대표 키워드. 등급 5의 넓은 카테고리어를 더 구체적인 단어로 교체. 등급 5와 어절 수가 같으면 반드시 다른 단어 조합 사용. 브랜드명·매장명 제외',
        5: '가장 범용적인 키워드. 제목 안에서 가장 넓은 범주를 나타내는 카테고리어 선택 (여러 하위 항목을 포괄하는 단어 우선). 브랜드명·매장명 제외. 반드시 2어절 이하',
    }.get(grade, '중간 키워드')

    length_guide = {
        1: '4~5어절 (제목이 짧으면 가능한 최대 어절)',
        2: '3~4어절',
        3: '2~3어절',
        4: '2어절',
        5: '1~2어절. 3어절 절대 금지',
    }.get(grade, '2~3어절')

    brand_rule = (
        '- 제목에 브랜드명·매장명이 있으면 키워드 마지막에 반드시 포함해.'
        if grade <= 2 else
        '- 브랜드명·매장명·고유 상호명은 키워드에서 제외해.'
    )

    inference_rule = (
        '- 제목에 있는 단어들을 최대한 조합해 구체적인 검색어를 만들어.'
        if grade <= 2 else
        '- 제목에 없는 지역명, 브랜드명, 업종은 추론해서 추가하지 마.'
    )

    return (
        f'아래 {len(titles)}개의 네이버 블로그 게시글 제목에서 각각 '
        f'네이버 블로그 검색 순위 확인용 키워드를 추출해.\n\n'
        f'키워드 등급은 1=세부 롱테일, 5=대표 주제이며 현재 등급은 {grade}야.\n'
        f'등급 기준: {detail_guide}\n\n'
        f'규칙:\n'
        f'- 각 제목마다 {count}개 이하의 키워드를 keywords 배열에 넣어.\n'
        f'- 키워드 길이: {length_guide}.\n'
        f'- 키워드는 네이버 검색창에 직접 입력하는 자연스러운 형태로 작성해.\n'
        f'  단어 순서: 장소/대상 → 특징/수식어 → 서비스/제품 카테고리 순.\n'
        f'{brand_rule}\n'
        f'{inference_rule}\n'
        f'- "후기", "추천", "방문", "정리", "리뷰", "내돈내산"처럼 검색어로 단독 사용이 어색한 단어는 제외해.\n'
        f'- 너무 넓은 단어 하나만 있는 키워드와 광고 문구형 키워드는 제외해.\n'
        f'- 등급 4와 5의 어절 수가 같을 때: 제목에 상하위 카테고리어가 있으면 5는 상위어·4는 하위어 선택.\n'
        f'  상하위 구분이 없으면 소재·타입 vs 기능·용도처럼 서로 다른 차원의 단어 조합 사용.\n'
        f'- 제목이 짧아 어절 수를 맞추기 어려우면, 어절 수보다 단어 선택 구체성으로 차별화해.\n'
        f'  (등급 5는 가장 범용적인 단어, 등급 1은 가장 구체적인 단어)\n'
        f'- 결과는 입력 번호와 같은 index를 반드시 포함해.\n\n'
        f'제목 목록:\n{titles_text}\n\n'
        f'JSON만 출력해. 예시:\n'
        f'{{"results":[{{"index":1,"title":"원본 제목","keywords":["키워드A","키워드B"]}}]}}'
    )


def _normalize_keyword_results(data: dict, titles: list, count: int) -> dict:
    mapping = {title: [] for title in titles}

    for position, item in enumerate(data.get('results', []), 1):
        if not isinstance(item, dict):
            continue

        index = _coerce_index(item.get('index'), fallback=position)
        if index is None or not 1 <= index <= len(titles):
            continue

        title = titles[index - 1]
        mapping[title] = _clean_keywords(item.get('keywords', []), title, count)

    return mapping


def _coerce_index(value, fallback: int):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _clean_keywords(keywords: list, title: str, count: int) -> list:
    cleaned = []
    seen = set()

    for keyword in keywords:
        if not isinstance(keyword, str):
            continue

        normalized = re.sub(r'\s+', ' ', keyword).strip()
        normalized = normalized.strip(' "\'.,;:()[]{}')
        if not _is_valid_keyword(normalized, title):
            continue

        key = normalized.casefold()
        if key in seen:
            continue

        cleaned.append(normalized)
        seen.add(key)
        if len(cleaned) >= count:
            break

    return cleaned


def _is_valid_keyword(keyword: str, title: str) -> bool:
    if len(keyword) < 2:
        return False

    tokens = re.findall(r'[가-힣A-Za-z0-9]+', keyword)
    meaningful_tokens = [token for token in tokens if len(token) >= 2]
    return len(meaningful_tokens) >= 1
