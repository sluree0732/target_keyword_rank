import requests

_URL = 'https://mitfasiqmftonblgreua.supabase.co/rest/v1/blog_lists'
_KEY = 'sb_publishable_LGiL6rFjGBrT9HQ_Tcn1nQ_Jo5MCsyn'
_HEADERS = {
    'apikey': _KEY,
    'Authorization': f'Bearer {_KEY}',
    'Content-Type': 'application/json',
}


def get_all() -> list:
    resp = requests.get(
        _URL,
        headers=_HEADERS,
        params={'select': '*', 'order': 'id.asc'},
        timeout=10,
    )
    resp.raise_for_status()
    return [{'name': r['name'], 'ids': r['ids']} for r in resp.json()]


def save(name: str, ids: list) -> None:
    check = requests.get(
        _URL,
        headers=_HEADERS,
        params={'name': f'eq.{name}', 'select': 'id'},
        timeout=10,
    )
    check.raise_for_status()

    if check.json():
        requests.patch(
            _URL,
            headers={**_HEADERS, 'Prefer': 'return=minimal'},
            params={'name': f'eq.{name}'},
            json={'ids': ids},
            timeout=10,
        ).raise_for_status()
    else:
        requests.post(
            _URL,
            headers={**_HEADERS, 'Prefer': 'return=minimal'},
            json={'name': name, 'ids': ids},
            timeout=10,
        ).raise_for_status()


def delete(name: str) -> None:
    requests.delete(
        _URL,
        headers=_HEADERS,
        params={'name': f'eq.{name}'},
        timeout=10,
    ).raise_for_status()
