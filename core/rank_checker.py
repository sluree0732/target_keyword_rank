import re
import time
import random

from curl_cffi import requests as curl_req

from utils.url_parser import normalize_blog_url

RESULTS_PER_PAGE = 10
MAX_RESULTS = 100


def _build_session() -> curl_req.Session:
    """Chrome 핑거프린트로 네이버 쿠키를 획득한 세션 반환."""
    session = curl_req.Session(impersonate='chrome120')
    try:
        session.get('https://www.naver.com/', timeout=10)
        time.sleep(random.uniform(1.2, 2.0))
    except Exception:
        pass
    return session


def check_rank(keyword: str, target_post_url: str) -> int:
    """
    네이버 블로그탭에서 keyword 검색 후 target_post_url 순위 반환.
    찾으면 1-based 순위, 못 찾으면 -1.
    """
    target_blog_id, target_post_no = normalize_blog_url(target_post_url)
    if not target_blog_id:
        return -1

    session = _build_session()
    rank = 0
    max_pages = MAX_RESULTS // RESULTS_PER_PAGE

    for page in range(max_pages):
        start = page * RESULTS_PER_PAGE + 1
        links = _fetch_result_links(session, keyword, start)

        if not links:
            break

        for link in links:
            rank += 1
            link_blog_id, link_post_no = normalize_blog_url(link)

            if link_blog_id == target_blog_id:
                if not target_post_no or not link_post_no or link_post_no == target_post_no:
                    return rank

        time.sleep(random.uniform(1.5, 2.5))

    return -1


def _fetch_result_links(session: curl_req.Session, keyword: str, start: int) -> list:
    try:
        resp = session.get(
            'https://search.naver.com/search.naver',
            params={'where': 'blog', 'query': keyword, 'start': start},
            headers={'Referer': 'https://www.naver.com/'},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return _extract_blog_links(resp.text)
    except Exception:
        return []


def _extract_blog_links(html: str) -> list:
    """HTML에서 blog.naver.com 게시글 링크만 추출 (중복 제거)."""
    seen = set()
    result = []

    # 패턴 1: /blog_id/post_no 형식 직접 추출
    for blog_id, post_no in re.findall(r'blog\.naver\.com/(\w+)/(\d+)', html):
        link = f'https://blog.naver.com/{blog_id}/{post_no}'
        if link not in seen:
            seen.add(link)
            result.append(link)

    # 패턴 2: PostView 쿼리스트링 형식 정규화
    for blog_id, post_no in re.findall(
        r'blogId=([^&"\']+)&(?:amp;)?logNo=(\d+)', html
    ):
        link = f'https://blog.naver.com/{blog_id}/{post_no}'
        if link not in seen:
            seen.add(link)
            result.append(link)

    return result
