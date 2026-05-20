def assemble_keywords(metadata: list, titles: list, grade: int, count: int) -> dict:
    mapping = {title: [] for title in titles}
    fn = {5: _g5, 4: _g4, 3: _g3, 2: _g2, 1: _g1}.get(grade)
    if fn is None:
        return mapping

    for meta in metadata:
        if not isinstance(meta, dict):
            continue
        title = meta.get('title', '')
        if title not in mapping:
            continue
        mapping[title] = _dedupe(fn(meta))[:count]

    return mapping


def _g5(m: dict) -> list:
    """UI 1등급: 1~2어절, 가장 광범위한 핵심 검색어"""
    cat = m.get('category') or ''
    place = m.get('place') or ''
    bname = m.get('brand_name') or ''
    btype = m.get('brand_type') or ''

    if not cat:
        return []

    out = []
    if place:
        out.append(_j(place, cat))
    if btype == 'recognition' and bname:
        out.append(_j(bname, cat))
    return out or [cat]


def _g4(m: dict) -> list:
    """UI 2등급: 2~3어절, 세부장소 또는 탐색의도어 포함"""
    cat = m.get('category') or ''
    place = m.get('place') or ''
    sub_place = m.get('sub_place') or ''
    intent = m.get('intent_word') or ''
    attrs = m.get('attributes') or []
    bname = m.get('brand_name') or ''
    btype = m.get('brand_type') or ''

    if not cat:
        return []

    out = []
    if sub_place:
        out.append(_j(sub_place, cat))
    if intent:
        out.append(_j(cat, intent))
    if btype == 'recognition' and bname and intent:
        out.append(_j(bname, intent))
    if attrs:
        out.append(_j(attrs[0], cat))

    return out or [_j(place, cat) if place else cat]


def _g3(m: dict) -> list:
    """UI 3등급: 2~3어절, 카테고리+특성 조합"""
    cat = m.get('category') or ''
    sub_cat = m.get('sub_category') or ''
    place = m.get('place') or ''
    attrs = m.get('attributes') or []
    bname = m.get('brand_name') or ''
    btype = m.get('brand_type') or ''

    if not cat:
        return []

    out = []
    if place and sub_cat:
        out.append(_j(place, cat, sub_cat))
    elif sub_cat:
        out.append(_j(cat, sub_cat))
    if btype == 'recognition' and bname and sub_cat:
        out.append(_j(bname, sub_cat))
    for attr in attrs[:2]:
        out.append(_j(cat, attr))

    return out or [_j(place, cat) if place else cat]


def _g2(m: dict) -> list:
    """UI 4등급: 상호명 필수, 없으면 []"""
    cat = m.get('category') or ''
    place = m.get('place') or ''
    sub_cat = m.get('sub_category') or ''
    bname = m.get('brand_name') or ''
    btype = m.get('brand_type') or ''
    intent = m.get('intent_word') or ''

    if not bname:
        return []

    out = []
    if btype == 'local':
        if place and cat:
            out.append(_j(place, cat, bname))
        elif cat:
            out.append(_j(cat, bname))
    elif btype == 'recognition':
        if sub_cat:
            out.append(_j(bname, sub_cat))
        if intent:
            out.append(_j(bname, intent))
        if cat:
            out.append(_j(bname, cat))
    elif btype == 'product':
        if cat:
            out.append(_j(bname, cat))
        if sub_cat:
            out.append(_j(bname, sub_cat))

    return out


def _g1(m: dict) -> list:
    """UI 5등급: 가장 세부적, 절대 [] 반환 금지"""
    cat = m.get('category') or ''
    sub_cat = m.get('sub_category') or ''
    place = m.get('place') or ''
    attrs = m.get('attributes') or []
    bname = m.get('brand_name') or ''
    btype = m.get('brand_type') or ''

    out = []
    if bname:
        if btype == 'local':
            if place and sub_cat:
                out.append(_j(place, sub_cat, bname))
            if place and cat:
                out.append(_j(place, cat, bname))
            if attrs and cat:
                out.append(_j(cat, attrs[0], bname))
        elif btype == 'recognition':
            if attrs and sub_cat:
                out.append(_j(bname, attrs[0], sub_cat))
            elif sub_cat:
                out.append(_j(bname, sub_cat))
            for attr in attrs[:2]:
                out.append(_j(bname, attr, cat))
        elif btype == 'product':
            if attrs and cat:
                out.append(_j(bname, attrs[0], cat))
            if cat:
                out.append(_j(bname, cat))

    if not out:
        if cat and sub_cat and attrs:
            out.append(_j(cat, sub_cat, attrs[0]))
        elif place and cat and sub_cat:
            out.append(_j(place, cat, sub_cat))
        elif attrs and cat:
            out.append(_j(attrs[0], cat))
        elif cat and sub_cat:
            out.append(_j(cat, sub_cat))
        elif place and cat:
            out.append(_j(place, cat))
        elif cat:
            out.append(cat)

    return out


def _j(*parts: str) -> str:
    return ' '.join(p for p in parts if p)


def _dedupe(keywords: list) -> list:
    seen = set()
    result = []
    for kw in keywords:
        k = kw.casefold()
        if k not in seen:
            seen.add(k)
            result.append(kw)
    return result
