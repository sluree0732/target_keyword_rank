import re
import time
import random

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_req

from utils.url_parser import normalize_blog_url


def create_session() -> curl_req.Session:
    """분석 시작 시 1회만 호출 — 이후 모든 키워드 검색에서 재사용."""
    session = curl_req.Session(impersonate='chrome120')
    try:
        session.get('https://www.naver.com/', timeout=10)
        time.sleep(random.uniform(0.8, 1.2))
    except Exception:
        pass
    return session


def check_rank(
    keyword: str,
    target_post_url: str,
    session: curl_req.Session,
    limit: int = 10,
) -> int:
    """
    네이버 블로그탭에서 keyword 검색 후 target_post_url의 순위 반환.

    순위 계산 방식: blog_id 기준 첫 등장 위치
    (Naver는 같은 블로그의 서브포스팅을 함께 노출하므로 blog 단위로 순위 산정)

    반환값:
        1 이상  → 실제 순위
        0       → limit 범위 내 없음 (UI에서 '-' 표시)
    """
    target_blog_id, _ = normalize_blog_url(target_post_url)
    if not target_blog_id:
        return 0

    results_per_page = 10
    max_pages = max(1, (limit + results_per_page - 1) // results_per_page)

    unique_rank = 0   # 중복 제거 후 순위
    seen_blogs: set = set()

    for page in range(max_pages):
        start = page * results_per_page + 1
        cards = _fetch_result_cards(session, keyword, start)

        if not cards:
            break

        for card_url in cards:
            card_blog_id, _ = normalize_blog_url(card_url)
            if not card_blog_id or card_blog_id in seen_blogs:
                continue  # 서브결과(같은 블로그 반복) 제외

            seen_blogs.add(card_blog_id)
            unique_rank += 1

            if unique_rank > limit:
                return 0

            if card_blog_id == target_blog_id:
                return unique_rank

        time.sleep(random.uniform(0.8, 1.2))

    return 0


def _fetch_result_cards(
    session: curl_req.Session, keyword: str, start: int
) -> list:
    """네이버 블로그탭 검색결과에서 카드 순서대로 블로그 URL 추출."""
    try:
        resp = session.get(
            'https://search.naver.com/search.naver',
            params={
                'ssc': 'tab.blog.all',
                'sm': 'tab_jum',
                'query': keyword,
                'start': start,
            },
            headers={'Referer': 'https://www.naver.com/'},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return _parse_result_cards(resp.text)
    except Exception:
        return []


def _parse_result_cards(html: str) -> list:
    """
    메인 검색결과 영역에서만 카드 URL을 순서대로 추출.
    각 포스팅 URL 기준 중복 제거(서브결과 포함 방지).
    사이드바 / 추천 / 광고 섹션 제외.
    """
    soup = BeautifulSoup(html, 'lxml')

    # ── 메인 검색결과 컨테이너 한정 ──────────────────────────────
    main = (
        soup.find('div', id='main_pack')
        or soup.find('section', {'data-type': re.compile(r'blog', re.I)})
        or soup
    )

    seen = set()
    results = []

    def add_unique(url: str):
        if url and url not in seen:
            seen.add(url)
            results.append(url)

    # 시도 1 : 타이틀 링크 클래스 직접 선택 — 메인 결과만 (서브결과 제외)
    # 네이버 블로그탭 타이틀 링크: api_txt_lines 또는 title_link 클래스
    title_links = main.select(
        'a.api_txt_lines.total_tit, '
        'a.title_link, '
        'a.api_txt_lines[href*="blog.naver.com"]'
    )
    if title_links:
        for a in title_links:
            norm = _normalize_href(a.get('href', ''))
            add_unique(norm)
        if results:
            return results

    # 시도 2 : li.bx 카드 단위 — 카드당 첫 번째 링크만
    cards = main.select('li.bx')
    if cards:
        for card in cards:
            # 카드 내에서 타이틀 링크 우선, 없으면 첫 번째 blog 링크
            title_a = card.select_one('a.api_txt_lines, a.title_link')
            url = _normalize_href(title_a.get('href', '')) if title_a else _first_blog_link(card)
            add_unique(url)
        if results:
            return results

    # 시도 3 : fallback — 전체 blog 링크 순서대로
    for a in main.find_all('a', href=True):
        norm = _normalize_href(a['href'])
        add_unique(norm)

    return results


def _first_blog_link(tag) -> str:
    """카드 태그에서 첫 번째 blog.naver.com 링크 추출."""
    for a in tag.find_all('a', href=True):
        norm = _normalize_href(a['href'])
        if norm:
            return norm
    return ''


def _normalize_href(href: str) -> str:
    """
    blog.naver.com/{blog_id}/{post_no} 형식만 허용.
    post_no 가 숫자여야 유효한 포스팅 URL.
    """
    if 'blog.naver.com' not in href:
        return ''

    # PostView 쿼리스트링 형식
    bid = re.search(r'blogId=([^&]+)', href)
    lno = re.search(r'logNo=(\d+)', href)
    if bid and lno:
        return f'https://blog.naver.com/{bid.group(1)}/{lno.group(1)}'

    # /blog_id/post_no 경로 형식
    m = re.search(r'blog\.naver\.com/([^/?#]+)/(\d+)', href)
    if m:
        return f'https://blog.naver.com/{m.group(1)}/{m.group(2)}'

    return ''
