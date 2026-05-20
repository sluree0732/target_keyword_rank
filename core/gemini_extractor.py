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
            '반드시 1~2어절. 3어절 이상 절대 금지.\n'
            '  형태: 장소+카테고리 또는 서비스·매장 브랜드+카테고리.\n'
            '  예: 광안리 술집 / 이삭토스트 메뉴 / 크로커다일 양산 / 여성청결제 / 소고기 뭣국\n'
            '  브랜드 포함 기준:\n'
            '    ○ 포함: 서비스·매장 브랜드(이삭토스트·스타벅스·크로커다일 등)\n'
            '    ✕ 제외: 제품 브랜드(포마이도터·디어오늘·한의비책 등 특정 제품명) → 카테고리만 추출\n'
            '  지역 상호명(맹구포차·메리윤 등)과 맛집·추천·구매처 등 탐색 의도어는 포함 금지.'
        ),
        4: (  # UI 2등급
            '2~3어절. 탐색 의도어를 반드시 포함. (제목에 없어도 이 등급만 추가 허용)\n'
            '  형태 ①: 세부 장소(동·역·구)+카테고리+탐색 의도어\n'
            '  형태 ②: 재료·특성+카테고리+탐색 의도어\n'
            '  형태 ③: 서비스·매장 브랜드+탐색 의도어\n'
            '  탐색 의도어 선택 기준 (아래 유형에서 제목 맥락에 맞게 반드시 추가):\n'
            '    음식·음료·카페 → 맛집, 추천, 먹는곳\n'
            '    제품·용품·화장품·건강식품 → 구매처, 추천, 효능\n'
            '    레시피·요리·집밥 → 레시피, 만들기, 방법\n'
            '    여행·드라이브·나들이 → 코스, 추천, 가볼만한곳\n'
            '  지역 상호명·제품 브랜드는 제외.'
        ),
        3: (  # UI 3등급
            '2~3어절. 카테고리+구체 특성 조합.\n'
            '  형태: 재료+카테고리 / 카테고리+콘텐츠유형 / 카테고리+성분·사양\n'
            '  예: 소고기 뭣국 / 광안리 술집 안주 / 소고기 뭣국 레시피 / 소고기 뭣국 집밥\n'
            '      이삭토스트 햄 스페셜 / 암막 우양산 / 당근 이유식\n'
            '  허용 콘텐츠유형: 레시피·집밥·만들기·효능·방법·성분 (구체 특성으로 사용 가능)\n'
            '  금지: 맛집·추천·구매처·가볼만한곳처럼 검색 목적만 나타내는 단어\n'
            '  서비스·매장 브랜드(이삭토스트·크로커다일 등)는 포함 가능.\n'
            '  지역 상호명(맹구포차·메리윤 등)은 제외.'
        ),
        2: (  # UI 4등급
            '2~3어절. 상호명이 반드시 포함된 검색어.\n'
            '  형태 ①: 장소+카테고리+지역상호명\n'
            '  형태 ②: 서비스·매장 브랜드+구체메뉴명·특성 (브랜드+카테고리만은 등급1과 겹치므로 금지)\n'
            '  형태 ③: 제품 브랜드+카테고리\n'
            '  예: 해운대 파스타 메리윤 / 이삭토스트 햄 스페셜 / 노스페이스 경량 패딩 / 포마이도터 여성청결제\n'
            '  금지 예: 이삭토스트 메뉴 (브랜드+카테고리만 → 등급1과 동일)\n'
            '  제목에 상호명이 없으면: 재료·특성+카테고리 조합으로 추출. 빈 배열 []은 반환하지 마.'
        ),
        1: (  # UI 5등급 (세부)
            '2~4어절. 가장 구체적인 롱테일 검색어.\n'
            '  형태: 구체 카테고리+상호명 / 구체 특성+상호명 / 브랜드명+구체 메뉴·제품·성분\n'
            '  예: 해운대 브런치 메리윤 / 이삭토스트 햄 스페셜 토스트 / 포마이도터 약산성 여성청결제\n'
            '  상호명이 없으면: 재료+카테고리+콘텐츠유형 또는 재료+성분+카테고리 세부 조합.\n'
            '  절대로 빈 배열 []로 반환하지 마.'
        ),
    }[grade]

    return (
        f'아래 {len(titles)}개의 네이버 블로그 게시글 제목에서 각각 '
        f'네이버 블로그 검색 순위 확인용 키워드를 {count}개 이하로 추출해.\n\n'
        f'현재 등급: {grade} (1=세부 롱테일, 5=대표)\n\n'
        f'[등급 {grade} 추출 기준]\n{grade_spec}\n\n'
        f'[공통 규칙]\n'
        f'- 탐색 의도어 정의: 맛집·추천·구매처·가볼만한곳처럼 검색 목적 자체를 나타내는 단어.\n'
        f'  레시피·집밥·만들기·효능·방법·성분처럼 콘텐츠 내용을 설명하는 단어는\n'
        f'  탐색 의도어가 아닌 구체 특성으로 간주한다.\n'
        f'- 브랜드·장소가 없어 키워드가 카테고리 1어절만 남을 때,\n'
        f'  제목의 주재료·성분·대상을 추가해 최소 2어절로 구성해.\n'
        f'- 키워드는 제목에 실제로 있는 글자·단어만 사용해. (등급 4의 탐색 의도어만 예외)\n'
        f'- 형용사·서술어 형태(강력하다·예쁘다·맛있다 등 ~하다/~이다/~다로 끝나는 묘사 단어)는 키워드에 포함하지 마.\n'
        f'- 후기·방문·정리·리뷰·내돈내산처럼 검색어로 단독 사용이 어색한 단어는 제외해.\n'
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
