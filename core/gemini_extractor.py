import hashlib
import json

_metadata_cache: dict = {}

_METADATA_SCHEMA = {
    'type': 'object',
    'properties': {
        'results': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'index': {'type': 'integer'},
                    'place': {'type': 'string'},
                    'sub_place': {'type': 'string'},
                    'category': {'type': 'string'},
                    'sub_category': {'type': 'string'},
                    'attributes': {'type': 'array', 'items': {'type': 'string'}},
                    'brand_name': {'type': 'string'},
                    'brand_type': {'type': 'string'},
                    'intent_word': {'type': 'string'},
                },
                'required': ['index', 'category'],
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
    from core.keyword_assembler import assemble_keywords

    metadata = _get_metadata(titles, api_key)
    return assemble_keywords(metadata, titles, grade, count)


def _get_metadata(titles: list, api_key: str) -> list:
    cache_key = hashlib.md5('|'.join(titles).encode()).hexdigest()
    if cache_key in _metadata_cache:
        return _metadata_cache[cache_key]

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    response = model.generate_content(
        _build_prompt(titles),
        generation_config={
            'response_mime_type': 'application/json',
            'response_schema': _METADATA_SCHEMA,
            'temperature': 0.1,
            'candidate_count': 1,
        },
    )

    data = json.loads(response.text)
    metadata = _parse_metadata(data, titles)
    _metadata_cache[cache_key] = metadata
    return metadata


def _build_prompt(titles: list) -> str:
    titles_text = '\n'.join(f'{i + 1}. {t}' for i, t in enumerate(titles))
    return (
        f'아래 {len(titles)}개의 네이버 블로그 게시글 제목에서 키워드 추출용 메타데이터를 추출해.\n\n'
        '필드 설명:\n'
        '- place: 광역 장소 (시·군·구·랜드마크 수준. 없으면 빈 문자열)\n'
        '- sub_place: 세부 장소 (동·역 수준. 없으면 빈 문자열)\n'
        '- category: 주요 서비스/제품 카테고리 (예: 술집, 여성청결제, 파스타. 없으면 빈 문자열)\n'
        '- sub_category: 세부 카테고리 (예: 안주, 브런치, 토스트. 없으면 빈 문자열)\n'
        '- attributes: 카테고리를 수식하는 특성 목록 (재료·성분·사양·조리법·가격대 등)\n'
        '  형용사/서술어(~하다/~이다/~다) 형태는 포함하지 마. 없으면 []\n'
        '- brand_name: 제목에 나오는 상호명 또는 브랜드명 (없으면 빈 문자열)\n'
        '- brand_type: 브랜드 유형 (없으면 빈 문자열)\n'
        '    local — 특정 지역 가게 고유명 (그 지역에서만 운영, 예: 맹구포차·메리윤·장춘향)\n'
        '    recognition — 전국 서비스·매장 브랜드 (체인·의류·생활용품, 예: 이삭토스트·스타벅스·크로커다일)\n'
        '    product — 특정 제품·성분 브랜드명 (예: 포마이도터·디어오늘·한의비책)\n'
        '- intent_word: 이 게시글을 검색할 때 쓸 탐색 의도어 1개\n'
        '  (맛집·구매처·효능·레시피·비교·이용방법 등 문맥에 맞게 자유롭게 생성)\n\n'
        '규칙:\n'
        '- 결과는 입력 번호와 같은 index를 반드시 포함해.\n\n'
        f'제목 목록:\n{titles_text}\n\n'
        'JSON만 출력해.'
    )


def _parse_metadata(data: dict, titles: list) -> list:
    results = [None] * len(titles)

    for pos, item in enumerate(data.get('results', []), 1):
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get('index', pos))
        except (TypeError, ValueError):
            idx = pos
        if not 1 <= idx <= len(titles):
            continue
        results[idx - 1] = _clean(item, idx, titles[idx - 1])

    for i, meta in enumerate(results):
        if meta is None:
            results[i] = _empty(i + 1, titles[i])

    return results


def _clean(item: dict, index: int, title: str) -> dict:
    def s(key):
        v = item.get(key, '')
        return v.strip() if isinstance(v, str) else ''

    def lst(key):
        v = item.get(key, [])
        if not isinstance(v, list):
            return []
        return [x.strip() for x in v if isinstance(x, str) and x.strip()]

    return {
        'index': index,
        'title': title,
        'place': s('place'),
        'sub_place': s('sub_place'),
        'category': s('category'),
        'sub_category': s('sub_category'),
        'attributes': lst('attributes'),
        'brand_name': s('brand_name'),
        'brand_type': s('brand_type'),
        'intent_word': s('intent_word'),
    }


def _empty(index: int, title: str) -> dict:
    return {
        'index': index,
        'title': title,
        'place': '',
        'sub_place': '',
        'category': '',
        'sub_category': '',
        'attributes': [],
        'brand_name': '',
        'brand_type': '',
        'intent_word': '',
    }
