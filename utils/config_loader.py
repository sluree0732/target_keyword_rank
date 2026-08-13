import json
import os
import sys


def load_config() -> dict:
    """config.json을 로드한다. EXE(PyInstaller) 실행 시 _MEIPASS 임시 폴더를 참조한다."""
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config.json')
    with open(config_path, encoding='utf-8') as f:
        return json.load(f)
