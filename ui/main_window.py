from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMainWindow, QSplitter

from core.analyzer import AnalyzerThread
from ui.left_panel import LeftPanel
from ui.right_panel import RightPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('타겟 키워드 노출 여부 분석')
        self.setMinimumSize(1100, 650)
        self.resize(1400, 800)
        self._analyzer = None

        splitter = QSplitter(Qt.Horizontal)
        self.left_panel = LeftPanel()
        self.right_panel = RightPanel()
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([400, 800])
        splitter.setHandleWidth(2)

        self.setCentralWidget(splitter)
        self.setStyleSheet('QMainWindow { background: #FAFAFA; }')

        self.left_panel.analyze_requested.connect(self._start_analysis)

    def _start_analysis(self, urls: list, post_count: int, keyword_count: int):
        if self._analyzer and self._analyzer.isRunning():
            self._analyzer.cancel()
            self._analyzer.wait()

        self.right_panel.clear_results()
        self.left_panel.set_analyzing(True)
        self.left_panel.update_status('분석 준비 중...')

        self._analyzer = AnalyzerThread(urls, post_count, keyword_count)
        self._analyzer.result_ready.connect(self.right_panel.add_result)
        self._analyzer.status_updated.connect(self.left_panel.update_status)
        self._analyzer.error_occurred.connect(self._on_error)
        self._analyzer.finished_all.connect(self._on_finished)
        self._analyzer.start()

    def _on_error(self, message: str):
        self.left_panel.update_status(f'⚠ {message}')

    def _on_finished(self):
        self.left_panel.set_analyzing(False)
        count = self.right_panel.table.rowCount()
        self.left_panel.update_status(f'분석 완료 — 총 {count}건')

    def closeEvent(self, event):
        if self._analyzer and self._analyzer.isRunning():
            self._analyzer.cancel()
            self._analyzer.wait()
        event.accept()
