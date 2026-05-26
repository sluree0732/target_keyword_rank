import requests

_URL = 'https://mitfasiqmftonblgreua.supabase.co/rest/v1/keyword_corrections'
_KEY = 'sb_publishable_LGiL6rFjGBrT9HQ_Tcn1nQ_Jo5MCsyn'
_HEADERS = {
    'apikey': _KEY,
    'Authorization': f'Bearer {_KEY}',
    'Content-Type': 'application/json',
}


def save(post_title: str, grade: int, keyword: str) -> None:
    requests.post(
        _URL,
        headers={**_HEADERS, 'Prefer': 'return=minimal'},
        json={'post_title': post_title, 'grade': grade, 'keyword': keyword},
        timeout=10,
    ).raise_for_status()


def fetch_by_grade(grade: int, limit: int = 5) -> list:
    resp = requests.get(
        _URL,
        headers=_HEADERS,
        params={
            'grade': f'eq.{grade}',
            'select': 'post_title,keyword',
            'order': 'created_at.desc',
            'limit': limit,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
