from PyQt5.QtCore import QThread, pyqtSignal

from core.blog_scraper import get_recent_posts
from core.keyword_extractor import extract_keywords
from core.rank_checker import check_rank
from utils.url_parser import extract_blog_id


class AnalyzerThread(QThread):
    result_ready = pyqtSignal(str, str, str, int)  # blog_url, post_title, keyword, rank
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished_all = pyqtSignal()

    def __init__(self, urls: list, post_count: int, keyword_count: int):
        super().__init__()
        self.urls = urls
        self.post_count = post_count
        self.keyword_count = keyword_count
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        for url in self.urls:
            if self._cancelled:
                break

            blog_id = extract_blog_id(url)
            if not blog_id:
                self.error_occurred.emit(f'URL 파싱 실패: {url}')
                continue

            self.status_updated.emit(f'게시글 수집 중... [{blog_id}]')

            try:
                posts = get_recent_posts(blog_id, self.post_count)
            except Exception as e:
                self.error_occurred.emit(f'{blog_id} 수집 실패: {e}')
                continue

            if not posts:
                self.error_occurred.emit(f'{blog_id}: 게시글을 찾을 수 없습니다')
                continue

            for post in posts:
                if self._cancelled:
                    break

                title = post['title']
                post_url = post['url']
                blog_url = f'blog.naver.com/{blog_id}'

                self.status_updated.emit(f'키워드 추출 중... [{title[:20]}]')
                keywords = extract_keywords(title, self.keyword_count)

                if not keywords:
                    self.error_occurred.emit(f'키워드 추출 실패: {title[:30]}')
                    continue

                for keyword in keywords:
                    if self._cancelled:
                        break

                    self.status_updated.emit(f'순위 확인 중... [{keyword}]')

                    try:
                        rank = check_rank(keyword, post_url)
                    except Exception:
                        rank = -1

                    self.result_ready.emit(blog_url, title, keyword, rank)

        self.finished_all.emit()
