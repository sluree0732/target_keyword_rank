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

    grade_spec = {
        5: (  # UI 1등급 (대표)
            '1~2어절. 가장 광범위한 핵심 검색어.\n'
            '  형태: 장소+카테고리 또는 서비스·매장 브랜드+카테고리.\n'
            '  예: 광안리 술집 / 이삭토스트 메뉴 / 크로커다일 양산 / 여성청결제 / 바디로션\n'
            '  브랜드 포함 기준:\n'
            '    ○ 포함: 서비스·매장 브랜드(이삭토스트·스타벅스·크로커다일 등)\n'
            '    ✕ 제외: 제품 브랜드(포마이도터·디어오늘·한의비책 등 특정 제품명) → 카테고리만 추출\n'
            '  지역 상호명(맹구포차·메리윤 등)과 탐색 의도어(맛집·추천 등)는 제외.'
        ),
        4: (  # UI 2등급
            '2~3어절. 세부 장소나 탐색 의도어가 포함된 검색어.\n'
            '  형태 ①: 세부 장소(동·역·구)+카테고리\n'
            '  형태 ②: 카테고리+탐색 의도어(맛집·카페·이용·구매처 등)\n'
            '  형태 ①②가 어려우면: 카테고리+구체 특성(재료·사양·조리법·성분 등)\n'
            '  예: 광안리 술집 맛집 / 약산성 여성청결제 / 이삭토스트 구매처\n'
            '  탐색 의도어는 제목에 없어도 추가 가능 (이 등급만 예외).\n'
            '  지역 상호명·제품 브랜드는 제외.'
        ),
        3: (  # UI 3등급
            '2~3어절. 카테고리·특성을 조합한 검색어.\n'
            '  형태: 카테고리+카테고리 또는 카테고리+구체 특성(재료·사양·조리법·성분 등)\n'
            '  예: 광안리 술집 안주 / 이삭토스트 햄 스페셜 토스트 / 암막 우양산 / 애호박전 레시피\n'
            '  서비스·매장 브랜드(이삭토스트·크로커다일 등)는 포함 가능.\n'
            '  지역 상호명(맹구포차·메리윤 등)은 제외.'
        ),
        2: (  # UI 4등급
            '2~3어절. 상호명이 반드시 포함된 검색어.\n'
            '  형태: 장소+카테고리+지역상호명 / 브랜드명+카테고리 (전국 브랜드)\n'
            '  예: 해운대 파스타 메리윤 / 부산역 중국집 장춘향 / 포마이도터 여성청결제 / 이삭토스트 메뉴\n'
            '  제목에 상호명(지역 가게 고유명 또는 전국 브랜드)이 없으면 keywords를 빈 배열 []로 반환해.'
        ),
        1: (  # UI 5등급 (세부)
            '2~4어절. UI 4등급보다 구체적인 롱테일 검색어.\n'
            '  형태: 구체 카테고리+상호명 / 구체 특성+상호명 / 브랜드명+구체 메뉴·제품·성분\n'
            '  예: 해운대 브런치 메리윤 / 이삭토스트 햄 스페셜 토스트 / 포마이도터 약산성 여성청결제\n'
            '  상호명이 없으면: 카테고리+구체 특성 조합으로 가장 세부적인 키워드 추출.\n'
            '  절대로 빈 배열 []로 반환하지 마.'
        ),
    }[grade]

    return (
        f'아래 {len(titles)}개의 네이버 블로그 게시글 제목에서 각각 '
        f'네이버 블로그 검색 순위 확인용 키워드를 {count}개 이하로 추출해.\n\n'
        f'현재 등급: {grade} (1=세부 롱테일, 5=대표)\n\n'
        f'[등급 {grade} 추출 기준]\n{grade_spec}\n\n'
        f'[공통 규칙]\n'
        f'- 키워드는 제목에 실제로 있는 글자·단어만 사용해. (등급 4의 탐색 의도어만 예외)\n'
        f'- 형용사·서술어 형태(강력하다·예쁘다·맛있다 등 ~하다/~이다/~다로 끝나는 묘사 단어)는 키워드에 포함하지 마.\n'
        f'- 후기·추천·방문·정리·리뷰·내돈내산처럼 검색어로 단독 사용이 어색한 단어는 제외해.\n'
        f'- 광의어 단어 하나만 있는 키워드와 광고 문구형 키워드는 제외해.\n'
        f'- 단어 순서: 장소/대상 → 특징/수식어 → 서비스/제품 카테고리.\n'
        f'- 대화체·일기형 제목으로 검색 가능한 명사·카테고리·장소가 전혀 없으면 keywords를 빈 배열 []로 반환해.\n'
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
