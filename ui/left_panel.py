from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
BTN_SMALL = (
    'QPushButton {'
    '  background-color: #FFFFFF; color: #374151;'
    '  border: 1px solid #CBD5E1; border-radius: 5px; padding: 0 10px;'
    '}'
    'QPushButton:hover { background-color: #EFF6FF; border-color: #93C5FD; }'
)


class LeftPanel(QWidget):
    # blog_ids, post_count, keyword_count, rank_limit, keyword_grades (list)
    analyze_requested = pyqtSignal(object, int, int, int, object)
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(320)
        self.setMaximumWidth(420)
        self._post_count = 5
        self._post_count_btns = []
        self._kw_count = 0
        self._kw_count_btns = []
        self._kw_grades = []
        self._kw_grade_btns = []
        self._multi_grade_mode = False
        self._is_analyzing = False
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

        add_list_btn = QPushButton('추가하기')
        add_list_btn.setFixedHeight(26)
        add_list_btn.setCursor(Qt.PointingHandCursor)
        add_list_btn.setStyleSheet(BTN_SMALL)
        add_list_btn.clicked.connect(self._on_add_list_clicked)

        load_list_btn = QPushButton('불러오기')
        load_list_btn.setFixedHeight(26)
        load_list_btn.setCursor(Qt.PointingHandCursor)
        load_list_btn.setStyleSheet(BTN_SMALL)
        load_list_btn.clicked.connect(self._on_load_list_clicked)

        id_header = QHBoxLayout()
        id_header.addWidget(id_label)
        id_header.addStretch()
        id_header.addWidget(add_list_btn)
        id_header.addWidget(load_list_btn)

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

        layout.addLayout(id_header)
        layout.addWidget(id_hint)
        layout.addWidget(self.url_input)

        # 최근 게시물 추출 개수 (토글 버튼 1~5)
        layout.addSpacing(8)
        layout.addLayout(self._make_toggle_row(
            '최근 게시물 추출 개수', 1, 5, 5,
            self._post_count_btns,
            self._on_post_count_clicked,
        ))

        # 키워드 추출 개수 (토글 버튼 1~5)
        layout.addSpacing(8)
        layout.addLayout(self._make_toggle_row(
            '키워드 추출 개수', 1, 5, 0,
            self._kw_count_btns,
            self._on_kw_count_clicked,
        ))

        # 키워드 등급 (단일/다중선택 토글 버튼)
        layout.addSpacing(8)
        layout.addLayout(self._make_grade_multi_btns())

        # 순위 탐색 범위 (텍스트 입력)
        layout.addSpacing(8)
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
        self.analyze_btn.installEventFilter(self)
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

    def _make_grade_multi_btns(self) -> QVBoxLayout:
        outer = QVBoxLayout()
        outer.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(QLabel('키워드 등급  (1=대표  ↔  5=세부)'))
        header.addStretch()

        self._multi_grade_btn = QPushButton('다중선택')
        self._multi_grade_btn.setFixedHeight(26)
        self._multi_grade_btn.setCursor(Qt.PointingHandCursor)
        self._multi_grade_btn.setStyleSheet(BTN_SMALL)
        self._multi_grade_btn.clicked.connect(self._toggle_multi_grade_mode)
        header.addWidget(self._multi_grade_btn)
        outer.addLayout(header)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        for n in range(1, 6):
            btn = QPushButton(str(n))
            btn.setFixedSize(46, 36)
            btn.setFont(QFont('', 11, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(BTN_NORMAL)
            btn.clicked.connect(lambda _, val=n: self._on_grade_btn_clicked(val))
            self._kw_grade_btns.append(btn)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        outer.addLayout(btn_row)
        return outer

    def _toggle_multi_grade_mode(self):
        self._multi_grade_mode = not self._multi_grade_mode
        self._multi_grade_btn.setStyleSheet(
            BTN_SELECTED if self._multi_grade_mode else BTN_NORMAL
        )
        if not self._multi_grade_mode and len(self._kw_grades) > 1:
            # 다중선택 해제 시 마지막 선택 등급 하나만 유지
            self._kw_grades = [self._kw_grades[-1]]
            self._refresh_grade_btns()

    def _on_grade_btn_clicked(self, grade: int):
        if self._multi_grade_mode:
            if grade in self._kw_grades:
                self._kw_grades.remove(grade)
            else:
                self._kw_grades.append(grade)
        else:
            self._kw_grades = [grade]
        self._refresh_grade_btns()

    def _refresh_grade_btns(self):
        for i, btn in enumerate(self._kw_grade_btns):
            btn.setStyleSheet(BTN_SELECTED if (i + 1) in self._kw_grades else BTN_NORMAL)

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

    def eventFilter(self, obj, event):
        if obj is self.analyze_btn and self._is_analyzing:
            if event.type() == QEvent.Enter:
                self.analyze_btn.setText('분석 중지')
            elif event.type() == QEvent.Leave:
                self.analyze_btn.setText('분석 중')
        return super().eventFilter(obj, event)

    def _on_analyze_clicked(self):
        if self._is_analyzing:
            self.stop_requested.emit()
            return

        text = self.url_input.toPlainText().strip()
        blog_ids = [line.strip() for line in text.splitlines() if line.strip()]

        if not blog_ids:
            self.status_label.setText('블로그 ID를 입력해주세요.')
            return

        seen: set = set()
        unique_ids = []
        for bid in blog_ids:
            if bid not in seen:
                seen.add(bid)
                unique_ids.append(bid)
        dup_count = len(blog_ids) - len(unique_ids)
        if dup_count > 0:
            reply = QMessageBox.question(
                self,
                '중복 블로그 ID 발견',
                f'중복된 블로그 ID {dup_count}개가 발견되었습니다.\n제거 후 분석을 시작할까요?',
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Ok,
            )
            if reply != QMessageBox.Ok:
                return
            self.url_input.setPlainText('\n'.join(unique_ids))
            blog_ids = unique_ids

        if self._kw_count == 0:
            self.status_label.setText('키워드 추출 개수를 선택해주세요.')
            return

        try:
            rank_limit = int(self.rank_limit_input.text().strip())
            if rank_limit < 1:
                raise ValueError
        except ValueError:
            self.status_label.setText('순위 탐색 범위를 올바른 숫자로 입력해주세요.')
            return

        grades = sorted(self._kw_grades)
        if not grades:
            self.status_label.setText('키워드 등급을 선택해주세요.')
            return

        self.analyze_requested.emit(
            blog_ids,
            self._post_count,
            self._kw_count,
            rank_limit,
            grades,
        )

    def set_analyzing(self, analyzing: bool):
        self._is_analyzing = analyzing
        self.progress_bar.setVisible(analyzing)
        if analyzing:
            self.progress_bar.setRange(0, 0)
            self.analyze_btn.setText('분석 중')
            self.analyze_btn.setStyleSheet(
                'QPushButton {'
                '  background-color: #6B7280; color: white;'
                '  border-radius: 6px; border: none;'
                '}'
                'QPushButton:hover { background-color: #DC2626; }'
                'QPushButton:pressed { background-color: #B91C1C; }'
            )
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.analyze_btn.setText('분석 시작')
            self.analyze_btn.setStyleSheet(
                'QPushButton {'
                '  background-color: #1D4F91; color: white;'
                '  border-radius: 6px; border: none;'
                '}'
                'QPushButton:hover { background-color: #2563EB; }'
                'QPushButton:pressed { background-color: #1E3A8A; }'
                'QPushButton:disabled { background-color: #A7B0BA; }'
            )

    def _on_add_list_clicked(self):
        from ui.blog_list_dialogs import AddEditDialog
        AddEditDialog(self).exec_()

    def _on_load_list_clicked(self):
        from ui.blog_list_dialogs import LoadDialog
        dlg = LoadDialog(self)
        if dlg.exec_() == LoadDialog.Accepted and dlg.selected_ids:
            self.url_input.setPlainText('\n'.join(dlg.selected_ids))

    def update_status(self, message: str):
        self.status_label.setText(message)
