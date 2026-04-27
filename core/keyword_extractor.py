import re

# kiwipiepy 없어도 동작하도록 fallback 처리
try:
    from kiwipiepy import Kiwi
    _kiwi = Kiwi()
    _USE_KIWI = True
except Exception:
    _kiwi = None
    _USE_KIWI = False

NOISE_WORDS = {
    '후기', '리뷰', '방문', '소개', '이야기', '이번', '이날', '이곳',
    '처음', '마지막', '최근', '이후', '방법', '내용', '이름', '하기',
    '오늘', '어제', '드디어', '정말', '진짜', '완전', '너무', '조금',
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
    '망미', '민락', '정관', '일광', '기장읍', '온천장', '부평',
    # 서울 주요 지역
    '강남', '강북', '홍대', '신촌', '명동', '이태원', '압구정', '청담',
    '여의도', '종로', '신림', '건대', '성수', '왕십리', '마포', '용산',
    # 기타 주요 도시
    '수원', '성남', '고양', '용인', '부천', '안산', '안양', '창원',
    '청주', '전주', '포항', '제주시', '서귀포',
}

CATEGORY_KEYWORDS = {
    '맛집', '식당', '카페', '횟집', '고기집', '음식점', '레스토랑',
    '이자카야', '술집', '포차', '분식', '베이커리', '디저트',
    '숙소', '펜션', '호텔', '모텔', '게스트하우스',
    '쇼핑', '마트', '시장', '관광지', '명소',
}


def extract_keywords(title: str, count: int = 3) -> list:
    nouns = _extract_nouns(title)
    if not nouns:
        return []

    location_nouns = [n for n in nouns if n in LOCATION_KEYWORDS]
    category_nouns = [n for n in nouns if n in CATEGORY_KEYWORDS]
    other_nouns = [n for n in nouns if n not in LOCATION_KEYWORDS and n not in CATEGORY_KEYWORDS]

    scored = {}

    def add(kw, score):
        if kw and len(kw) > 1:
            scored[kw] = max(scored.get(kw, 0), score)

    # 지역 + 카테고리 (최우선: 실제 검색 패턴)
    for loc in location_nouns:
        for cat in category_nouns:
            add(f'{loc} {cat}', 20)

    # 지역 + 음식/업종명 (other)
    for loc in location_nouns:
        for other in other_nouns:
            add(f'{loc} {other}', 15)

    # 지역 + 다른지역 + 카테고리 (삼중 조합)
    for loc in location_nouns:
        for other in other_nouns:
            for cat in category_nouns:
                add(f'{loc} {other} {cat}', 18)
        for i in range(len(location_nouns)):
            for cat in category_nouns:
                if location_nouns[i] != loc:
                    add(f'{loc} {location_nouns[i]} {cat}', 17)

    # 지역 + 두 other
    for loc in location_nouns:
        for i in range(len(other_nouns) - 1):
            add(f'{loc} {other_nouns[i]} {other_nouns[i+1]}', 12)

    # 연속 bigram (지역 없어도)
    for i in range(len(nouns) - 1):
        kw = f'{nouns[i]} {nouns[i+1]}'
        score = 8
        if nouns[i] in LOCATION_KEYWORDS or nouns[i+1] in LOCATION_KEYWORDS:
            score += 4
        if nouns[i] in CATEGORY_KEYWORDS or nouns[i+1] in CATEGORY_KEYWORDS:
            score += 2
        add(kw, score)

    # 연속 trigram
    for i in range(len(nouns) - 2):
        kw = f'{nouns[i]} {nouns[i+1]} {nouns[i+2]}'
        score = 6
        if any(n in LOCATION_KEYWORDS for n in [nouns[i], nouns[i+1], nouns[i+2]]):
            score += 4
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

    # kiwipiepy 추출 명사
    for token in tokens:
        if token.tag in ('NNG', 'NNP') and len(token.form) >= 2:
            if token.form not in NOISE_WORDS and token.form not in seen:
                seen.add(token.form)
                result.append(token.form)

    # 원본 어절(띄어쓰기 단위) 중 kiwipiepy가 분리한 복합 단어 복원
    # 예: "연막창" → "연" + "막창" 으로 분리됐을 때 원본 "연막창" 추가
    for word in re.findall(r'[가-힣]{3,}', title):
        if word not in seen and word not in NOISE_WORDS:
            # 이 단어가 추출된 명사들의 조합으로 이루어진 경우 원본 단어를 우선 추가
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
