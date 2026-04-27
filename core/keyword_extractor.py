import re

try:
    from kiwipiepy import Kiwi
    _kiwi = Kiwi()
    _USE_KIWI = True
except Exception:
    _kiwi = None
    _USE_KIWI = False

# 단독으로 쓰이면 의미 없는 단어
NOISE_WORDS = {
    '후기', '리뷰', '방문', '소개', '이야기', '이번', '이날', '이곳',
    '처음', '마지막', '최근', '이후', '방법', '내용', '이름', '하기',
    '오늘', '어제', '드디어', '정말', '진짜', '완전', '너무', '조금',
    '아이',   # "아이랑" → "아이" 오추출 방지
    '혼자',   # 단독 키워드로 의미 없음
    '추천',   # 다른 단어 없이 단독 사용 불가
    '비교', '정리', '모음', '위치', '시간', '가격',
}

LOCATION_KEYWORDS = {
    # 광역시 / 도
    '서울', '부산', '인천', '대구', '광주', '대전', '울산', '세종', '제주',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남',
    # 부산 구/군
    '중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구',
    '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장',
    # 부산 주요 지역/역
    '해운대', '광안리', '남포동', '서면', '장산', '센텀', '동래', '수영',
    '망미', '민락', '정관', '일광', '기장읍', '온천장', '부평', '전포',
    # 서울 주요 지역
    '강남', '강북', '홍대', '신촌', '명동', '이태원', '압구정', '청담',
    '여의도', '종로', '신림', '건대', '성수', '왕십리', '마포', '용산',
    # 기타 주요 도시
    '수원', '성남', '고양', '용인', '부천', '안산', '안양', '창원',
    '청주', '전주', '포항', '제주시', '서귀포',
}

# 업종 카테고리
CATEGORY_KEYWORDS = {
    '맛집', '식당', '카페', '횟집', '고기집', '음식점', '레스토랑',
    '이자카야', '술집', '포차', '분식', '베이커리', '디저트',
    '숙소', '펜션', '호텔', '모텔', '게스트하우스',
    '쇼핑', '마트', '시장', '관광지', '명소',
    # 여행 의도 키워드 — "부산 가볼만한곳" 같은 형태에 쓰임
    '가볼만한곳', '여행', '데이트', '코스', '드라이브', '나들이',
    '산책', '피크닉', '스냅', '뷰맛집', '야경',
}


def extract_keywords(title: str, count: int = 3) -> list:
    nouns = _extract_nouns(title)
    if not nouns:
        return []

    location_nouns = [n for n in nouns if n in LOCATION_KEYWORDS]
    category_nouns = [n for n in nouns if n in CATEGORY_KEYWORDS]
    # 지역도 카테고리도 아닌 고유명사 (브랜드명 등)
    other_nouns = [
        n for n in nouns
        if n not in LOCATION_KEYWORDS and n not in CATEGORY_KEYWORDS
    ]

    scored = {}

    def add(kw: str, score: int):
        kw = kw.strip()
        if kw and len(kw) > 1:
            scored[kw] = max(scored.get(kw, 0), score)

    # ── 지역 + 카테고리 (최우선: 실제 검색 패턴) ──────────────────
    for loc in location_nouns:
        for cat in category_nouns:
            add(f'{loc} {cat}', 20)

    # ── 지역 + 브랜드/고유명사 ────────────────────────────────────
    for loc in location_nouns:
        for other in other_nouns:
            add(f'{loc} {other}', 16)

    # ── 지역(소) + 지역(대) + 카테고리: 예) 해운대구 부산 맛집 ────
    # 단, 지역+지역만의 조합(카테고리 없음)은 생성하지 않음
    for i, loc1 in enumerate(location_nouns):
        for j, loc2 in enumerate(location_nouns):
            if i == j:
                continue
            for cat in category_nouns:
                add(f'{loc1} {loc2} {cat}', 17)

    # ── 지역 + 브랜드 + 카테고리 삼중 조합 ──────────────────────
    for loc in location_nouns:
        for other in other_nouns:
            for cat in category_nouns:
                add(f'{loc} {other} {cat}', 18)

    # ── 연속 bigram (지역+지역 단독 조합은 제외) ──────────────────
    for i in range(len(nouns) - 1):
        n1, n2 = nouns[i], nouns[i + 1]
        # 지역+지역 단독 조합 제외 (검색량 낮음)
        if n1 in LOCATION_KEYWORDS and n2 in LOCATION_KEYWORDS:
            continue
        kw = f'{n1} {n2}'
        score = 8
        if n1 in LOCATION_KEYWORDS or n2 in LOCATION_KEYWORDS:
            score += 4
        if n1 in CATEGORY_KEYWORDS or n2 in CATEGORY_KEYWORDS:
            score += 3
        add(kw, score)

    # ── 연속 trigram ──────────────────────────────────────────────
    for i in range(len(nouns) - 2):
        n1, n2, n3 = nouns[i], nouns[i + 1], nouns[i + 2]
        trio = [n1, n2, n3]
        # 3개 모두 지역이면 제외
        if all(n in LOCATION_KEYWORDS for n in trio):
            continue
        kw = f'{n1} {n2} {n3}'
        score = 6
        if any(n in LOCATION_KEYWORDS for n in trio):
            score += 4
        if any(n in CATEGORY_KEYWORDS for n in trio):
            score += 3
        add(kw, score)

    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in ranked[:count]]


def _extract_nouns(title: str) -> list:
    if _USE_KIWI:
        return _kiwi_nouns(title)
    return _regex_nouns(title)


def _kiwi_nouns(title: str) -> list:
    tokens = _kiwi.tokenize(title)
    seen = set()
    result = []

    for token in tokens:
        if token.tag in ('NNG', 'NNP') and len(token.form) >= 2:
            if token.form not in NOISE_WORDS and token.form not in seen:
                seen.add(token.form)
                result.append(token.form)

    # 복합 고유명사 복원: "연막창" → "연"+"막창" 으로 분리된 경우 원본 추가
    for word in re.findall(r'[가-힣]{3,}', title):
        if word not in seen and word not in NOISE_WORDS:
            covered = any(word.startswith(n) or word.endswith(n) for n in result if n in word)
            if covered or not any(word in n for n in result):
                seen.add(word)
                result.append(word)

    return result


def _regex_nouns(title: str) -> list:
    words = re.findall(r'[가-힣]{2,}', title)
    seen = set()
    result = []
    for w in words:
        if w not in NOISE_WORDS and w not in seen:
            seen.add(w)
            result.append(w)
    return result
