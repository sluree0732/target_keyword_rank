import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'ko-KR,ko;q=0.9',
}

MOBILE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) '
        'Version/16.0 Mobile/15E148 Safari/604.1'
    ),
    'Accept-Language': 'ko-KR,ko;q=0.9',
}


def get_blog_data(blog_id: str, count: int) -> dict:
    """
    모바일 블로그 페이지에서 오늘 방문자수 수집,
    RSS 피드에서 최근 N개 게시글 수집.

    반환: {'visitor_today': int, 'posts': [{'title', 'url', 'blog_id'}]}
    """
    visitor_today = _fetch_visitor_count(blog_id)

    try:
        posts = _fetch_via_rss(blog_id, count)
    except Exception:
        posts = _fetch_via_html(blog_id, count)

    return {'visitor_today': visitor_today, 'posts': posts}


def _fetch_visitor_count(blog_id: str) -> int:
    """모바일 블로그 페이지에서 오늘 방문자수 파싱. 실패 시 0 반환."""
    try:
        url = (
            f'https://m.blog.naver.com/{blog_id}'
            '?categoryNo=0&listStyle=post&tab=1'
        )
        resp = requests.get(url, headers=MOBILE_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        # 시도 1: 방문자 수 전용 요소 선택자
        for selector in [
            '.blog_visitor .num',
            '.visitorcnt',
            '.today_cnt',
            '.area_visit_today em',
            '.visitor_today',
            'em.num_today',
        ]:
            el = soup.select_one(selector)
            if el:
                m = re.search(r'\d+', el.get_text())
                if m:
                    return int(m.group())

        # 시도 2: 전체 텍스트에서 "오늘 N" 패턴 검색
        m = re.search(r'오늘\s+(\d[\d,]*)', soup.get_text())
        if m:
            return int(m.group(1).replace(',', ''))

    except Exception:
        pass

    return 0


def _fetch_via_rss(blog_id: str, count: int) -> list:
    url = f'https://rss.blog.naver.com/{blog_id}.xml'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    channel = root.find('channel')
    if channel is None:
        raise ValueError('RSS channel 없음')

    posts = []
    for item in channel.findall('item')[:count]:
        title = _clean_cdata(item.findtext('title', ''))
        link = _clean_cdata(item.findtext('link', ''))
        if title and link:
            posts.append({'title': title, 'url': link, 'blog_id': blog_id})

    if not posts:
        raise ValueError('RSS 게시글 없음')

    return posts


def _fetch_via_html(blog_id: str, count: int) -> list:
    url = f'https://blog.naver.com/{blog_id}'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'lxml')
    posts = []

    for a in soup.select('a[href*="/{}"]'.format(blog_id)):
        href = a.get('href', '')
        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        if not href.startswith('http'):
            href = 'https://blog.naver.com' + href
        posts.append({'title': title, 'url': href, 'blog_id': blog_id})
        if len(posts) >= count:
            break

    return posts


def _clean_cdata(text: str) -> str:
    return text.replace('<![CDATA[', '').replace(']]>', '').strip()
