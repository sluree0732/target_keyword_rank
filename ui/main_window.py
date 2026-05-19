import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplitter, QSystemTrayIcon

from core.analyzer import AnalyzerThread
from ui.left_panel import LeftPanel
from ui.right_panel import RightPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('타겟 키워드 노출 여부 분석')
        self.setMinimumSize(1180, 720)
        self.resize(1500, 820)
        self.setWindowIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        self._analyzer = None
        self._errors = []
        self._analysis_start: float = 0.0
        self._pending_grades: list = []
        self._analysis_blog_ids: list = []
        self._analysis_post_count: int = 5
        self._analysis_kw_count: int = 3
        self._analysis_rank_limit: int = 5

        splitter = QSplitter(Qt.Horizontal)
        self.left_panel = LeftPanel()
        self.right_panel = RightPanel()
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([360, 1000])
        splitter.setHandleWidth(1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        self.setCentralWidget(splitter)
        self.setStyleSheet(
            'QMainWindow { background: #F3F6FA; }'
            'QWidget { font-family: "Malgun Gothic"; font-size: 10pt; }'
            'QLabel { color: #111827; }'
            'QSplitter::handle { background: #D8DEE8; }'
        )

        self.left_panel.analyze_requested.connect(self._start_analysis)
        self.left_panel.stop_requested.connect(self._stop_analysis)
        self._center_on_screen()

        self._tray = QSystemTrayIcon(self.windowIcon(), self)
        self._tray.setToolTip('타겟 키워드 노출 여부 분석')
        self._tray.show()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _start_analysis(
        self,
        blog_ids: list,
        post_count: int,
        keyword_count: int,
        rank_limit: int,
        keyword_grades: list,
    ):
        if self._analyzer and self._analyzer.isRunning():
            self._analyzer.cancel()
            self._analyzer.wait()

        self._errors.clear()
        self._analysis_start = time.time()
        self._pending_grades = list(keyword_grades)
        self._analysis_blog_ids = blog_ids
        self._analysis_post_count = post_count
        self._analysis_kw_count = keyword_count
        self._analysis_rank_limit = rank_limit
        self._start_next_grade()

    def _start_next_grade(self):
        grade = self._pending_grades.pop(0)
        self.right_panel.start_new_analysis(grade, self._analysis_post_count, self._analysis_kw_count, self._analysis_rank_limit)
        self.right_panel.update_legend(self._analysis_rank_limit)
        self.left_panel.set_analyzing(True)
        self.left_panel.update_status('분석 준비 중...')

        internal_grade = 6 - grade
        self._analyzer = AnalyzerThread(
            self._analysis_blog_ids,
            self._analysis_post_count,
            self._analysis_kw_count,
            self._analysis_rank_limit,
            internal_grade,
        )
        self._analyzer.result_ready.connect(self.right_panel.add_result)
        self._analyzer.status_updated.connect(self.left_panel.update_status)
        self._analyzer.error_occurred.connect(self._on_error)
        self._analyzer.finished_all.connect(self.right_panel.flush_last_group)
        self._analyzer.finished_all.connect(self._on_grade_finished)
        self._analyzer.start()

    def _stop_analysis(self):
        self._pending_grades.clear()
        if self._analyzer and self._analyzer.isRunning():
            try:
                self._analyzer.finished_all.disconnect(self._on_grade_finished)
            except TypeError:
                pass
            self._analyzer.cancel()
            self._analyzer.wait()
        self.left_panel.set_analyzing(False)
        self.right_panel.flush_last_group()
        count = self.right_panel.result_count
        self.left_panel.update_status(f'분석 중단 — 총 {count}건 수집됨')

    def _on_error(self, message: str):
        self._errors.append(message)
        self.left_panel.update_status(f'⚠ {message}')

    def _on_grade_finished(self):
        if self._pending_grades:
            next_grade = self._pending_grades[0]
            self.left_panel.update_status(f'다음 등급({next_grade}등급) 분석 시작 중...')
            self._start_next_grade()
        else:
            self._on_all_finished()

    def _on_all_finished(self):
        self.left_panel.set_analyzing(False)
        count = self.right_panel.result_count
        self.left_panel.update_status(f'분석 완료 — 총 {count}건')
        elapsed = int(time.time() - self._analysis_start)
        minutes, seconds = divmod(elapsed, 60)
        elapsed_str = f'{minutes}분 {seconds}초' if minutes else f'{seconds}초'
        self._tray.showMessage(
            '분석 완료',
            f'총 {count}건 수집되었습니다.\n소요 시간: {elapsed_str}',
            QSystemTrayIcon.Information,
            5000,
        )

        if count == 0 and self._errors:
            error_text = '\n'.join(f'• {e}' for e in self._errors)
            msg = QMessageBox(self)
            msg.setWindowTitle('분석 오류')
            msg.setIcon(QMessageBox.Warning)
            msg.setText('분석 결과가 없습니다. 아래 오류를 확인해주세요.')
            msg.setDetailedText(error_text)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    def closeEvent(self, event):
        if self._analyzer and self._analyzer.isRunning():
            self._analyzer.cancel()
            self._analyzer.wait()
        self._tray.hide()
        event.accept()
