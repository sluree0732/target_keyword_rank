from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

BTN_SELECTED = (
    'QPushButton {'
    '  background-color: #1D4F91; color: white;'
    '  border: none; border-radius: 5px; font-weight: bold;'
    '}'
)
BTN_NORMAL = (
    'QPushButton {'
    '  background-color: #FFFFFF; color: #374151;'
    '  border: 1px solid #CBD5E1; border-radius: 5px;'
    '}'
    'QPushButton:hover { background-color: #EFF6FF; border-color: #93C5FD; }'
)


class LeftPanel(QWidget):
    # blog_ids, post_count, keyword_count, rank_limit, keyword_grade
    analyze_requested = pyqtSignal(object, int, int, int, int)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(320)
        self.setMaximumWidth(420)
        self._post_count = 5
        self._post_count_btns = []
        self._kw_count = 3
        self._kw_count_btns = []
        self._kw_grade = 3
        self._kw_grade_btns = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 20, 18, 18)

        title = QLabel('블로그 분석 설정')
        title.setFont(QFont('', 15, QFont.Bold))
        title.setStyleSheet('color: #111827;')
        layout.addWidget(title)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background: #E0E0E0;')
        layout.addWidget(sep)

        # 블로그 ID 입력
        id_label = QLabel('블로그 ID 입력')
        id_label.setFont(QFont('', 10, QFont.Bold))
        id_hint = QLabel('한 줄에 하나씩 입력하세요')
        id_hint.setStyleSheet('color: #757575; font-size: 9pt;')

        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText(
            'blog_id1\n'
            'blog_id2\n'
            'blog_id3'
        )
        self.url_input.setMinimumHeight(160)
        self.url_input.setStyleSheet(
            'QTextEdit {'
            '  background: white; border: 1px solid #CBD5E1;'
            '  border-radius: 6px; padding: 8px;'
            '}'
            'QTextEdit:focus { border-color: #2563EB; }'
        )

        layout.addWidget(id_label)
        layout.addWidget(id_hint)
        layout.addWidget(self.url_input)

        # 최근 게시물 추출 개수 (토글 버튼 1~5)
        layout.addLayout(self._make_toggle_row(
            '최근 게시물 추출 개수', 1, 5, 5,
            self._post_count_btns,
            self._on_post_count_clicked,
        ))

        # 키워드 추출 개수 (토글 버튼 1~5)
        layout.addLayout(self._make_toggle_row(
            '키워드 추출 개수', 1, 5, 3,
            self._kw_count_btns,
            self._on_kw_count_clicked,
        ))

        # 키워드 등급 (토글 버튼 1~5, 1=세부, 5=대표)
        layout.addLayout(self._make_toggle_row(
            '키워드 등급  (1=세부  ↔  5=대표)', 1, 5, 3,
            self._kw_grade_btns,
            self._on_kw_grade_clicked,
        ))

        # 순위 탐색 범위 (텍스트 입력)
        layout.addLayout(self._make_rank_limit_row())

        # 분석 시작 버튼
        self.analyze_btn = QPushButton('분석 시작')
        self.analyze_btn.setMinimumHeight(50)
        self.analyze_btn.setFont(QFont('', 12, QFont.Bold))
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #1D4F91; color: white;'
            '  border-radius: 6px; border: none;'
            '}'
            'QPushButton:hover { background-color: #2563EB; }'
            'QPushButton:pressed { background-color: #1E3A8A; }'
            'QPushButton:disabled { background-color: #A7B0BA; }'
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

    def _make_toggle_row(
        self,
        label_text: str,
        start: int,
        end: int,
        default: int,
        btn_list: list,
        handler,
    ) -> QVBoxLayout:
        outer = QVBoxLayout()
        outer.setSpacing(6)

        lbl = QLabel(label_text)
        outer.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        for n in range(start, end + 1):
            btn = QPushButton(str(n))
            btn.setFixedSize(46, 36)
            btn.setFont(QFont('', 11, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, val=n: handler(val))
            btn_list.append(btn)
            btn_row.addWidget(btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

        self._refresh_toggle_style(btn_list, default, start)
        return outer

    def _refresh_toggle_style(self, btn_list: list, selected: int, start: int = 1):
        for i, btn in enumerate(btn_list):
            btn.setStyleSheet(BTN_SELECTED if (i + start) == selected else BTN_NORMAL)

    def _on_post_count_clicked(self, value: int):
        self._post_count = value
        self._refresh_toggle_style(self._post_count_btns, value)

    def _on_kw_count_clicked(self, value: int):
        self._kw_count = value
        self._refresh_toggle_style(self._kw_count_btns, value)

    def _on_kw_grade_clicked(self, value: int):
        self._kw_grade = value
        self._refresh_toggle_style(self._kw_grade_btns, value)

    def _make_rank_limit_row(self) -> QVBoxLayout:
        outer = QVBoxLayout()
        outer.setSpacing(6)

        outer.addWidget(QLabel('순위 탐색 범위'))

        self.rank_limit_input = QLineEdit('5')
        self.rank_limit_input.setFixedWidth(76)
        self.rank_limit_input.setAlignment(Qt.AlignCenter)
        self.rank_limit_input.setStyleSheet(
            'QLineEdit { border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 6px; }'
            'QLineEdit:focus { border-color: #2563EB; }'
        )

        input_row = QHBoxLayout()
        input_row.setSpacing(4)
        input_row.addWidget(QLabel('상위'))
        input_row.addWidget(self.rank_limit_input)
        input_row.addWidget(QLabel('위'))
        input_row.addStretch()
        outer.addLayout(input_row)

        return outer

    def _on_analyze_clicked(self):
        text = self.url_input.toPlainText().strip()
        blog_ids = [line.strip() for line in text.splitlines() if line.strip()]

        if not blog_ids:
            self.status_label.setText('블로그 ID를 입력해주세요.')
            return

        try:
            rank_limit = int(self.rank_limit_input.text().strip())
            if rank_limit < 1:
                raise ValueError
        except ValueError:
            self.status_label.setText('순위 탐색 범위를 올바른 숫자로 입력해주세요.')
            return

        self.analyze_requested.emit(
            blog_ids,
            self._post_count,
            self._kw_count,
            rank_limit,
            self._kw_grade,
        )

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
