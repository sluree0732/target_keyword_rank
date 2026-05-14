from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplitter

from core.analyzer import AnalyzerThread
from ui.left_panel import LeftPanel
from ui.right_panel import RightPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('타겟 키워드 노출 여부 분석')
        self.setMinimumSize(1180, 720)
        self.resize(1360, 820)
        self.setWindowIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        self._analyzer = None
        self._errors = []

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
        keyword_grade: int,
    ):
        if self._analyzer and self._analyzer.isRunning():
            self._analyzer.cancel()
            self._analyzer.wait()

        self._errors.clear()
        self.right_panel.start_new_analysis(keyword_grade, post_count, keyword_count, rank_limit)
        self.right_panel.update_legend(rank_limit)
        self.left_panel.set_analyzing(True)
        self.left_panel.update_status('분석 준비 중...')

        internal_grade = 6 - keyword_grade  # UI 1(대표)→내부 5, UI 5(세부)→내부 1
        self._analyzer = AnalyzerThread(blog_ids, post_count, keyword_count, rank_limit, internal_grade)
        self._analyzer.result_ready.connect(self.right_panel.add_result)
        self._analyzer.status_updated.connect(self.left_panel.update_status)
        self._analyzer.error_occurred.connect(self._on_error)
        self._analyzer.finished_all.connect(self.right_panel.flush_last_group)
        self._analyzer.finished_all.connect(self._on_finished)
        self._analyzer.start()

    def _stop_analysis(self):
        if self._analyzer and self._analyzer.isRunning():
            self._analyzer.cancel()
            self._analyzer.wait()
        self.left_panel.set_analyzing(False)
        self.right_panel.flush_last_group()
        count = self.right_panel.result_count
        self.left_panel.update_status(f'분석 중단 — 총 {count}건 수집됨')

    def _on_error(self, message: str):
        self._errors.append(message)
        self.left_panel.update_status(f'⚠ {message}')

    def _on_finished(self):
        self.left_panel.set_analyzing(False)
        count = self.right_panel.result_count
        self.left_panel.update_status(f'분석 완료 — 총 {count}건')

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
        event.accept()
