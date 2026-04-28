from PyQt5.QtCore import QThread, pyqtSignal

from core.blog_scraper import get_blog_data
from core.keyword_extractor import extract_keywords
from core.rank_checker import create_session, check_rank


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
        rank_limit: int = 10,
    ):
        super().__init__()
        self.blog_ids = blog_ids
        self.post_count = post_count
        self.keyword_count = keyword_count
        self.rank_limit = rank_limit
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        self.status_updated.emit('네이버 연결 중...')
        session = create_session()

        for blog_id in self.blog_ids:
            if self._cancelled:
                break

            blog_id = blog_id.strip()
            if not blog_id:
                continue

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

            for post in posts:
                if self._cancelled:
                    break

                title = post['title']
                post_url = post['url']

                self.status_updated.emit(f'키워드 추출 중... [{title[:20]}]')
                keywords = extract_keywords(title, self.keyword_count)

                if not keywords:
                    self.error_occurred.emit(f'키워드 추출 실패: {title[:30]}')
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
