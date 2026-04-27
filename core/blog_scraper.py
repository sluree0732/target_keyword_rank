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


def get_recent_posts(blog_id: str, count: int) -> list:
    """RSS 피드로 최근 게시글 N개 반환. 실패 시 HTML 파싱 시도."""
    try:
        return _fetch_via_rss(blog_id, count)
    except Exception:
        return _fetch_via_html(blog_id, count)


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
