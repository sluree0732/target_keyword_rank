from urllib.parse import urlparse, parse_qs


def extract_blog_id(url: str) -> str:
    url = url.strip()
    if not url:
        return ''

    parsed = urlparse(url)

    if 'blog.naver.com' not in parsed.netloc:
        return ''

    # PostView.nhn?blogId=xxx 형식
    qs = parse_qs(parsed.query)
    if 'blogId' in qs:
        return qs['blogId'][0]

    # /blog_id/post_no 또는 /blog_id 형식
    path_parts = [p for p in parsed.path.strip('/').split('/') if p]
    if path_parts and path_parts[0] not in ('PostView.nhn', 'PostView.naver'):
        return path_parts[0]

    return ''


def normalize_blog_url(url: str) -> tuple:
    """(blog_id, post_no) 추출"""
    parsed = urlparse(url)

    qs = parse_qs(parsed.query)
    if 'blogId' in qs:
        blog_id = qs['blogId'][0]
        post_no = qs.get('logNo', [''])[0]
        return blog_id, post_no

    path_parts = [p for p in parsed.path.strip('/').split('/') if p]
    if len(path_parts) >= 2:
        return path_parts[0], path_parts[1]
    if len(path_parts) == 1:
        return path_parts[0], ''

    return '', ''
