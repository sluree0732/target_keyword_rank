import json
import os
import time

from PyQt5.QtCore import QThread, pyqtSignal

from core.blog_scraper import get_blog_data
from core.gemini_extractor import extract_keywords_batch
from core.rank_checker import check_rank, create_session

_RETRY_DELAYS = [15, 30, 60]


def _load_api_key() -> str:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    with open(config_path, encoding='utf-8') as f:
        return json.load(f)['gemini_api_key']


class AnalyzerThread(QThread):
    # blog_url, visitor_count, post_title, keyword, rank
    result_ready = pyqtSignal(str, int, str, str, int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished_all = pyqtSignal()

    def __init__(
        self,
        blog_ids: list,
        post_count: int,
        keyword_count: int,
        rank_limit: int,
        keyword_grade: int,
    ):
        super().__init__()
        self.blog_ids = blog_ids
        self.post_count = post_count
        self.keyword_count = keyword_count
        self.rank_limit = rank_limit
        self.keyword_grade = keyword_grade
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _call_gemini_with_retry(self, titles: list, api_key: str) -> dict:
        for attempt, delay in enumerate(_RETRY_DELAYS, 1):
            try:
                return extract_keywords_batch(
                    titles, self.keyword_grade, self.keyword_count, api_key
                )
            except Exception as e:
                err_str = str(e)
                is_rate_limit = '429' in err_str or 'quota' in err_str.lower()
                if is_rate_limit and attempt <= len(_RETRY_DELAYS):
                    self.status_updated.emit(
                        f'API 요청 한도 초과 — {delay}초 후 재시도 ({attempt}/{len(_RETRY_DELAYS)})'
                    )
                    for _ in range(delay):
                        if self._cancelled:
                            return {}
                        time.sleep(1)
                else:
                    raise
        return {}

    def run(self):
        try:
            api_key = _load_api_key()
        except Exception as e:
            self.error_occurred.emit(f'API 키 로드 실패: {e}')
            self.finished_all.emit()
            return

        self.status_updated.emit('네이버 연결 중...')
        session = create_session()

        for idx, blog_id in enumerate(self.blog_ids):
            if self._cancelled:
                break

            blog_id = blog_id.strip()
            if not blog_id:
                continue

            # 두 번째 블로그부터 5초 딜레이 (Gemini RPM 여유)
            if idx > 0:
                self.status_updated.emit('다음 블로그 처리 대기 중... (5초)')
                for _ in range(5):
                    if self._cancelled:
                        break
                    time.sleep(1)
                if self._cancelled:
                    break

            self.status_updated.emit(f'블로그 수집 중... [{blog_id}]')

            try:
                data = get_blog_data(blog_id, self.post_count)
            except Exception as e:
                self.error_occurred.emit(f'{blog_id} 수집 실패: {e}')
                continue

            posts = data.get('posts', [])
            visitor_count = data.get('visitor_today', 0)
            blog_url = f'blog.naver.com/{blog_id}'

            if not posts:
                self.error_occurred.emit(f'{blog_id}: 게시글을 찾을 수 없습니다')
                continue

            titles = [p['title'] for p in posts]
            self.status_updated.emit(
                f'키워드 추출 중... [{blog_id}] ({len(titles)}개 게시글 배치 처리)'
            )

            try:
                keyword_map = self._call_gemini_with_retry(titles, api_key)
            except Exception as e:
                self.error_occurred.emit(f'{blog_id} 키워드 추출 실패: {e}')
                continue

            if self._cancelled:
                break

            for post in posts:
                if self._cancelled:
                    break

                title = post['title']
                post_url = post['url']
                keywords = keyword_map.get(title, [])

                if not keywords:
                    self.error_occurred.emit(f'키워드 없음: {title[:30]}')
                    continue

                for keyword in keywords:
                    if self._cancelled:
                        break

                    self.status_updated.emit(
                        f'순위 확인 중... [{keyword}] (상위 {self.rank_limit}위)'
                    )

                    try:
                        rank = check_rank(keyword, post_url, session, self.rank_limit)
                    except Exception:
                        rank = 0

                    self.result_ready.emit(blog_url, visitor_count, title, keyword, rank)

        self.finished_all.emit()
