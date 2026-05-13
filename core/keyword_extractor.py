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
    '아이', '혼자', '추천', '비교', '정리', '모음', '위치', '시간', '가격',
}

LOCATION_KEYWORDS = {
    '서울', '부산', '인천', '대구', '광주', '대전', '울산', '세종', '제주',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남',
    '중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구',
    '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장',
    '해운대', '광안리', '남포동', '서면', '장산', '센텀', '동래', '수영',
    '망미', '민락', '정관', '일광', '기장읍', '온천장', '부평', '전포',
    '강남', '강북', '홍대', '신촌', '명동', '이태원', '압구정', '청담',
    '여의도', '종로', '신림', '건대', '성수', '왕십리', '마포', '용산',
    '수원', '성남', '고양', '용인', '부천', '안산', '안양', '창원',
    '청주', '전주', '포항', '제주시', '서귀포',
}

CATEGORY_KEYWORDS = {
    '맛집', '식당', '카페', '횟집', '고기집', '음식점', '레스토랑',
    '이자카야', '술집', '포차', '분식', '베이커리', '디저트',
    '숙소', '펜션', '호텔', '모텔', '게스트하우스',
    '쇼핑', '마트', '시장', '관광지', '명소',
    '가볼만한곳', '여행', '데이트', '코스', '드라이브', '나들이',
    '산책', '피크닉', '스냅', '뷰맛집', '야경',
}


def extract_keywords(title: str, count: int = 3) -> list:
    """
    제목에서 자연스러운 키워드 조합을 추출합니다.
    순서 보존(N-gram) + 지역명 우선순위 알고리즘 적용.
    """
    # 1. 전처리: 특수문자 제거 및 명사 추출
    clean_title = re.sub(r'[^가-힣0-9\s]', ' ', title)
    nouns = _extract_nouns(clean_title)
    
    if not nouns:
        return []

    scored = {}

    def add_score(kw: str, score: int):
        kw = kw.strip()
        if not kw or len(kw) < 2:
            return
        # 이미 존재하는 키워드라면 더 높은 점수 유지
        scored[kw] = max(scored.get(kw, 0), score)

    # 2. 지역명/카테고리 태깅
    is_loc = [n in LOCATION_KEYWORDS for n in nouns]
    is_cat = [n in CATEGORY_KEYWORDS for n in nouns]

    # 3. 전략 A: 순서 보존 N-gram (Bigram, Trigram)
    # 제목의 흐름을 깨지 않는 가장 자연스러운 검색어
    for i in range(len(nouns)):
        n1 = nouns[i]
        
        # 단일 명사 (기본 점수)
        base_score = 5
        if is_loc[i]: base_score += 5
        if is_cat[i]: base_score += 3
        add_score(n1, base_score)

        # Bigram (2개 조합)
        if i < len(nouns) - 1:
            n2 = nouns[i+1]
            kw2 = f"{n1} {n2}"
            score2 = 10
            if is_loc[i] or is_loc[i+1]: score2 += 5
            if is_cat[i] or is_cat[i+1]: score2 += 5
            # [지역 + 맛집] 조합 최고점
            if (is_loc[i] and is_cat[i+1]) or (is_cat[i] and is_loc[i+1]):
                score2 += 10
            add_score(kw2, score2)

        # Trigram (3개 조합)
        if i < len(nouns) - 2:
            n2, n3 = nouns[i+1], nouns[i+2]
            kw3 = f"{n1} {n2} {n3}"
            score3 = 8
            if any([is_loc[i], is_loc[i+1], is_loc[i+2]]): score3 += 5
            if any([is_cat[i], is_cat[i+1], is_cat[i+2]]): score3 += 5
            add_score(kw3, score3)

    # 4. 전략 B: 고정 패턴 (지역 + 업종)
    # 제목 내 순서가 떨어져 있어도 유효한 핵심 검색 패턴
    for i, loc in enumerate(nouns):
        if not is_loc[i]: continue
        for j, cat in enumerate(nouns):
            if not is_cat[j]: continue
            if i == j: continue
            # 제목에 있는 순서대로 조합
            kw = f"{loc} {cat}" if i < j else f"{cat} {loc}"
            add_score(kw, 25) # 가장 강력한 검색 의도

    # 5. 정렬 및 결과 반환
    # 소음 단어 포함된 경우 점수 대폭 삭감
    for kw in list(scored.keys()):
        if any(noise in kw.split() for noise in NOISE_WORDS):
            scored[kw] -= 15

    ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    
    # 중복 제거 (부분 집합인 키워드 제거 로직)
    final_keywords = []
    for kw, score in ranked:
        if any(kw in existing for existing in final_keywords):
            continue
        final_keywords.append(kw)
        if len(final_keywords) >= count:
            break
            
    return final_keywords


def _extract_nouns(title: str) -> list:
    if _USE_KIWI:
        return _kiwi_nouns(title)
    return _regex_nouns(title)


def _kiwi_nouns(title: str) -> list:
    tokens = _kiwi.tokenize(title)
    result = []
    for token in tokens:
        # 일반명사, 고유명사, 숫자(지명과 결합될 수 있음)
        if token.tag in ('NNG', 'NNP', 'SN'):
            form = token.form
            if form not in NOISE_WORDS:
                result.append(form)
    
    # Kiwi가 너무 잘게 쪼갠 경우 (예: "연막창" -> "연", "막창") 보정
    # 실제 제목에서 2글자 이상의 연속된 한글 덩어리 추출하여 보완
    chunks = re.findall(r'[가-힣]{2,}', title)
    for chunk in chunks:
        if chunk not in result and chunk not in NOISE_WORDS:
            # 기존 명사 리스트에 포함되지 않은 덩어리가 핵심 키워드일 확률이 높음
            if any(n in chunk for n in LOCATION_KEYWORDS) or any(n in chunk for n in CATEGORY_KEYWORDS):
                result.append(chunk)
                
    return result


def _regex_nouns(title: str) -> list:
    # 형태소 분석기 없을 때를 위한 단순 정규식 추출
    words = re.findall(r'[가-힣0-9]{2,}', title)
    return [w for w in words if w not in NOISE_WORDS]
