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

    response = model.generate_content(
        _build_prompt(titles, grade, count),
        generation_config={
            'response_mime_type': 'application/json',
            'response_schema': _KEYWORD_RESPONSE_SCHEMA,
            'temperature': 0.2,
            'candidate_count': 1,
        },
    )

    data = json.loads(response.text)
    return _normalize_keyword_results(data, titles, count)


def _build_prompt(titles: list, grade: int, count: int) -> str:
    titles_text = '\n'.join(f'{i + 1}. {title}' for i, title in enumerate(titles))
    detail_guide = {
        1: '가장 세부적인 롱테일 키워드. 지역, 대상, 업종, 구체 메뉴/서비스를 최대한 포함',
        2: '세부 키워드. 검색량보다 게시글과의 정확한 일치를 우선',
        3: '검색 순위 확인에 적합한 중간 길이 키워드. 너무 넓거나 너무 좁지 않게 선택',
        4: '대표성 있는 키워드. 단, 게시글 주제와 직접 관련된 범위 유지',
        5: '가장 대표적인 주제 키워드. 지나치게 일반적인 단어 하나는 피함',
    }.get(grade, '검색 순위 확인에 적합한 중간 길이 키워드')

    return (
        f'아래 {len(titles)}개의 네이버 블로그 게시글 제목에서 각각 '
        f'네이버 블로그 검색 순위 확인용 키워드를 추출해.\n\n'
        f'키워드 등급은 1=세부 롱테일, 5=대표 주제이며 현재 등급은 {grade}야.\n'
        f'등급 기준: {detail_guide}\n\n'
        f'규칙:\n'
        f'- 각 제목마다 정확히 {count}개 이하의 키워드를 keywords 배열에 넣어.\n'
        f'- 키워드는 실제 사용자가 네이버에서 검색할 만한 2~5어절 검색어로 작성해.\n'
        f'- 제목에 없는 지역명, 브랜드명, 업종을 추론하지 마.\n'
        f'- "후기", "추천", "방문", "정리", "리뷰"처럼 단독으로 의미가 약한 단어는 제외해.\n'
        f'- 너무 넓은 단어 하나만 있는 키워드와 광고 문구형 키워드는 제외해.\n'
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
    if not meaningful_tokens:
        return False

    normalized_title = re.sub(r'\s+', '', title).casefold()
    return all(token.casefold() in normalized_title for token in meaningful_tokens)
