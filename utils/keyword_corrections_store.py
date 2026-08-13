import requests

from utils.config_loader import load_config

_config = load_config()
_BACKEND = _config.get('backend', 'supabase')

_URL = 'https://mitfasiqmftonblgreua.supabase.co/rest/v1/keyword_corrections'
_KEY = 'sb_publishable_LGiL6rFjGBrT9HQ_Tcn1nQ_Jo5MCsyn'
_HEADERS = {
    'apikey': _KEY,
    'Authorization': f'Bearer {_KEY}',
    'Content-Type': 'application/json',
}

_azure_config = _config.get('azure', {})
_AZURE_BASE = _azure_config.get('function_base_url', '')
_AZURE_HEADERS = {
    'x-functions-key': _azure_config.get('function_key', ''),
    'Content-Type': 'application/json',
}


def save(post_title: str, grade: int, keyword: str) -> None:
    if _BACKEND == 'azure':
        requests.post(
            f'{_AZURE_BASE}/keyword_corrections',
            headers=_AZURE_HEADERS,
            json={'post_title': post_title, 'grade': grade, 'keyword': keyword},
            timeout=10,
        ).raise_for_status()
        return

    requests.post(
        _URL,
        headers={**_HEADERS, 'Prefer': 'return=minimal'},
        json={'post_title': post_title, 'grade': grade, 'keyword': keyword},
        timeout=10,
    ).raise_for_status()


def fetch_exact_matches(titles: list, grade: int) -> dict:
    """같은 등급의 저장된 정답 키워드를 반환. {post_title: keyword}"""
    if not titles:
        return {}

    if _BACKEND == 'azure':
        resp = requests.post(
            f'{_AZURE_BASE}/keyword_corrections/fetch',
            headers=_AZURE_HEADERS,
            json={'titles': titles, 'grade': grade},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    escaped = [t.replace('"', '""') for t in titles]
    in_value = 'in.(' + ','.join(f'"{t}"' for t in escaped) + ')'

    resp = requests.get(
        _URL,
        headers=_HEADERS,
        params={
            'grade': f'eq.{grade}',
            'post_title': in_value,
            'select': 'post_title,keyword,id',
            'order': 'id.desc',
        },
        timeout=10,
    )
    resp.raise_for_status()

    result = {}
    for row in resp.json():
        title = row['post_title']
        if title not in result:  # id.desc 순이므로 첫 번째가 최신
            result[title] = row['keyword']
    return result
