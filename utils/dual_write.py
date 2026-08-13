import logging


def try_secondary(func, *args) -> None:
    """이중 쓰기용 보조 백엔드 호출 — 실패해도 예외를 전파하지 않고 로그만 남긴다."""
    try:
        func(*args)
    except Exception:
        logging.exception('dual-write: 보조 백엔드 저장 실패 (%s)', func.__name__)
