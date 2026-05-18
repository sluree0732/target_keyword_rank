import json
import os
from pathlib import Path


def _data_path() -> Path:
    app_data = os.environ.get('APPDATA', str(Path.home()))
    folder = Path(app_data) / '타겟키워드분석'
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'blog_lists.json'


def _load_raw() -> dict:
    path = _data_path()
    if not path.exists():
        return {'lists': []}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {'lists': []}


def _save_raw(data: dict) -> None:
    _data_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def get_all() -> list:
    return _load_raw().get('lists', [])


def save(name: str, ids: list) -> None:
    data = _load_raw()
    lists = data.get('lists', [])
    for item in lists:
        if item['name'] == name:
            item['ids'] = ids
            _save_raw(data)
            return
    lists.append({'name': name, 'ids': ids})
    data['lists'] = lists
    _save_raw(data)


def delete(name: str) -> None:
    data = _load_raw()
    data['lists'] = [i for i in data.get('lists', []) if i['name'] != name]
    _save_raw(data)
