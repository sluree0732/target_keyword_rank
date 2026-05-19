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
        1: ('UI 4등급과 다른 카테고리 또는 구체항목+상호명 조합. '
            '세부 장소+상호명 또는 다른 카테고리+상호명 형태. '
            '상호명이 제목에 없으면 keywords를 빈 배열 []로 반환해. 최대 4어절.'),
        2: ('장소+핵심 카테고리+상호명. 상호명 반드시 포함. '
            '전국 브랜드면 브랜드명+카테고리 형태. '
            '상호명이 제목에 없으면 keywords를 빈 배열 []로 반환해. 2~3어절.'),
        3: ('넓은 장소+카테고리 2개 조합 또는 카테고리+구체 특성. '
            '상호명 제외. 탐색 의도어 없이. 2~3어절.'),
        4: ('세부 장소(동·역·구 등)로 교체하거나 탐색 의도어(맛집·카페·이용·구매처 등)를 추가. '
            '전국 브랜드면 브랜드+매장 타입+핵심 기능. 상호명 제외. 2~3어절. '
            '제목에서 카테고리를 파악할 수 없으면 keywords를 빈 배열 []로 반환해.'),
        5: ('가장 대표적인 넓은 장소/브랜드+핵심 카테고리. 상호명·매장명 제외. '
            '탐색 의도어 없이. 1~2어절.'),
    }.get(grade, '중간 키워드')

    length_guide = {
        1: '최대 4어절. 5어절 이상 절대 금지.',
        2: '2~3어절',
        3: '2~3어절',
        4: '2~3어절',
        5: '1~2어절',
    }.get(grade, '2~3어절')

    if grade == 5:  # UI 1등급 (대표)
        brand_rule = '- 상호명·매장명은 키워드에서 제외해. 장소+카테고리 핵심 조합만 사용해.'
    elif grade == 4:  # UI 2등급
        brand_rule = ('- 지역 상호명은 제외해. '
                      '전국 체인 브랜드의 매장 타입(리저브·올데이·딜리버리 등)은 세부 위치처럼 포함 가능.')
    elif grade == 3:  # UI 3등급
        brand_rule = '- 상호명·매장명은 키워드에서 제외해. 넓은 장소+구체 항목 조합에 집중.'
    elif grade == 2:  # UI 4등급
        brand_rule = ('- 지역 상호명이 있으면 반드시 "장소+카테고리+상호명" 형태로 구성해.\n'
                      '  (예: 해운대 파스타 메리윤, 부산역 중국집 장춘향, 양산 옷수선 사계절옷수선)\n'
                      '- 전국 브랜드면 브랜드명+카테고리 형태.\n'
                      '- 상호명이 제목에 없으면 keywords를 빈 배열 []로 반환해.')
    else:  # grade == 1, UI 5등급 (세부)
        brand_rule = ('- 상호명 반드시 포함. UI 4등급에서 사용하지 않은 다른 카테고리 또는 구체항목과 상호명을 조합해.\n'
                      '  (예: 해운대 브런치 메리윤, 부산역 자이나타운 장춘향, 양산 중부동 사계절옷수선)\n'
                      '- 상호명이 제목에 없으면 keywords를 빈 배열 []로 반환해.')

    if grade == 1:  # UI 5등급 (세부)
        inference_rule = (
            '- 제목에 있는 단어들을 조합해 구체적인 검색어를 만들어.\n'
            '- 상호명(지역명·카테고리어·수식어가 아닌 고유 명사)이 없으면 빈 배열 []로 반환해.\n'
            '- 탐색 의도어(맛집·후기·추천 등)는 포함하지 마.'
        )
    elif grade == 2:  # UI 4등급
        inference_rule = (
            '- 제목에 있는 단어들을 최대한 조합해 구체적인 검색어를 만들어.\n'
            '- 제목에 없는 단어는 어떤 이유로도 사용 금지.\n'
            '  제목의 의미·맥락·주제를 해석해 카테고리·분류어를 파악하거나 생성하는 것 포함.\n'
            '- 상호명(지역명·카테고리어·수식어가 아닌 고유 명사)이 없으면 빈 배열 []로 반환해.'
        )
    elif grade == 4:  # UI 2등급
        inference_rule = (
            '- 제목에 없는 단어는 추가하지 마. 단, 탐색 의도어(맛집·카페·이용·구매처 등)는 예외.\n'
            '- 제목에 실제로 등장하지 않는 글자·단어는 어떠한 이유로도 사용 금지.'
            ' Gemini가 해당 가게·브랜드에 대해 알고 있는 메뉴·업종·특징도 사용 금지.'
        )
    elif grade == 5:  # UI 1등급 (대표)
        inference_rule = (
            '- 제목에 없는 단어는 추가하지 마.\n'
            '- 탐색 의도어(맛집·카페·이용·추천·구매처 등)는 제목에 있어도 키워드에서 제외해.\n'
            '- 장소+카테고리 핵심 조합만 사용해. 수식어 붙이지 마.'
        )
    else:  # grade == 3, UI 3등급
        inference_rule = (
            '- 제목에 없는 단어는 어떤 이유로도 추가하지 마.\n'
            '- 제목에 실제로 등장하지 않는 글자·단어는 어떠한 이유로도 사용 금지.'
            ' Gemini가 해당 가게·브랜드에 대해 알고 있는 메뉴·업종·특징도 사용 금지.'
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
        f'- [필수] 키워드는 반드시 제목에 실제로 있는 글자·단어의 조합이어야 해.\n'
        f'  Gemini가 제목의 주제·분류·업종을 파악하더라도 그 판단 결과를 키워드에 삽입 금지.\n'
        f'- [필수] 제목이 대화체·감상·일기 형식으로 검색 가능한 명사·카테고리·장소가 없으면\n'
        f'  keywords를 빈 배열 []로 반환해. 억지로 키워드를 생성하지 마.\n'
        f'- "후기", "추천", "방문", "정리", "리뷰", "내돈내산"처럼 검색어로 단독 사용이 어색한 단어는 제외해.\n'
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
    return len(meaningful_tokens) >= 1
