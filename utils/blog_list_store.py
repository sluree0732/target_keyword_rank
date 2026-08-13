import requests

from utils.config_loader import load_config

_config = load_config()
_BACKEND = _config.get('backend', 'supabase')

_URL = 'https://mitfasiqmftonblgreua.supabase.co/rest/v1/blog_lists'
_KEY = 'sb_publishable_LGiL6rFjGBrT9HQ_Tcn1nQ_Jo5MCsyn'
_HEADERS = {
    'apikey': _KEY,
    'Authorization': f'Bearer {_KEY}',
    'Content-Type': 'application/json',
}

_azure_config = _config.get('azure', {})
_AZURE_URL = f"{_azure_config.get('function_base_url', '')}/blog_lists"
_AZURE_HEADERS = {
    'x-functions-key': _azure_config.get('function_key', ''),
    'Content-Type': 'application/json',
}


def get_all() -> list:
    if _BACKEND == 'azure':
        resp = requests.get(_AZURE_URL, headers=_AZURE_HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()

    resp = requests.get(
        _URL,
        headers=_HEADERS,
        params={'select': '*', 'order': 'id.asc'},
        timeout=10,
    )
    resp.raise_for_status()
    return [{'name': r['name'], 'ids': r['ids']} for r in resp.json()]


def save(name: str, ids: list) -> None:
    if _BACKEND == 'azure':
        requests.post(
            _AZURE_URL,
            headers=_AZURE_HEADERS,
            json={'name': name, 'ids': ids},
            timeout=10,
        ).raise_for_status()
        return

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
    if _BACKEND == 'azure':
        requests.delete(
            _AZURE_URL,
            headers=_AZURE_HEADERS,
            params={'name': name},
            timeout=10,
        ).raise_for_status()
        return

    requests.delete(
        _URL,
        headers=_HEADERS,
        params={'name': f'eq.{name}'},
        timeout=10,
    ).raise_for_status()
