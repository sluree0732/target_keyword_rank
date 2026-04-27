from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LeftPanel(QWidget):
    analyze_requested = pyqtSignal(object, int, int)  # urls, post_count, keyword_count

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(340)
        self.setMaximumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel('블로그 분석 설정')
        title.setFont(QFont('', 13, QFont.Bold))
        layout.addWidget(title)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background: #E0E0E0;')
        layout.addWidget(sep)

        # URL 입력
        url_label = QLabel('블로그 주소 입력')
        url_label.setFont(QFont('', 10, QFont.Bold))
        url_hint = QLabel('한 줄에 하나씩 입력하세요')
        url_hint.setStyleSheet('color: #757575; font-size: 9pt;')

        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText(
            'https://blog.naver.com/blog_id/post_no\n'
            'https://blog.naver.com/blog_id2/post_no2'
        )
        self.url_input.setMinimumHeight(200)
        self.url_input.setStyleSheet(
            'QTextEdit { border: 1px solid #BDBDBD; border-radius: 4px; padding: 6px; }'
            'QTextEdit:focus { border-color: #1976D2; }'
        )

        layout.addWidget(url_label)
        layout.addWidget(url_hint)
        layout.addWidget(self.url_input)

        # 최근 게시물 개수
        post_row = QHBoxLayout()
        post_label = QLabel('최근 게시물 제목 추출 개수')
        self.post_count = QSpinBox()
        self.post_count.setRange(1, 20)
        self.post_count.setValue(2)
        self.post_count.setFixedWidth(70)
        self.post_count.setSuffix(' 개')
        post_row.addWidget(post_label)
        post_row.addStretch()
        post_row.addWidget(self.post_count)
        layout.addLayout(post_row)

        # 키워드 추출 개수
        kw_row = QHBoxLayout()
        kw_label = QLabel('키워드 추출 개수')
        self.kw_count = QSpinBox()
        self.kw_count.setRange(1, 10)
        self.kw_count.setValue(3)
        self.kw_count.setFixedWidth(70)
        self.kw_count.setSuffix(' 개')
        kw_row.addWidget(kw_label)
        kw_row.addStretch()
        kw_row.addWidget(self.kw_count)
        layout.addLayout(kw_row)

        # 분석 시작 버튼
        self.analyze_btn = QPushButton('분석 시작')
        self.analyze_btn.setMinimumHeight(44)
        self.analyze_btn.setFont(QFont('', 11, QFont.Bold))
        self.analyze_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #1565C0;'
            '  color: white;'
            '  border-radius: 6px;'
            '  border: none;'
            '}'
            'QPushButton:hover { background-color: #1976D2; }'
            'QPushButton:pressed { background-color: #0D47A1; }'
            'QPushButton:disabled { background-color: #90A4AE; }'
        )
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self.analyze_btn)

        # 진행 상태
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(
            'QProgressBar { border: none; background: #E3F2FD; border-radius: 3px; }'
            'QProgressBar::chunk { background: #1976D2; border-radius: 3px; }'
        )
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #616161; font-size: 9pt;')
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _on_analyze_clicked(self):
        text = self.url_input.toPlainText().strip()
        urls = [line.strip() for line in text.splitlines() if line.strip()]

        if not urls:
            self.status_label.setText('블로그 주소를 입력해주세요.')
            return

        self.analyze_requested.emit(urls, self.post_count.value(), self.kw_count.value())

    def set_analyzing(self, analyzing: bool):
        self.analyze_btn.setEnabled(not analyzing)
        self.progress_bar.setVisible(analyzing)
        if analyzing:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)

    def update_status(self, message: str):
        self.status_label.setText(message)
