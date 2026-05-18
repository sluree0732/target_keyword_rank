from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils import blog_list_store

_BTN_NORMAL = (
    'QPushButton {'
    '  background-color: #FFFFFF; color: #374151;'
    '  border: 1px solid #CBD5E1; border-radius: 5px;'
    '}'
    'QPushButton:hover { background-color: #EFF6FF; border-color: #93C5FD; }'
)
_BTN_PRIMARY = (
    'QPushButton {'
    '  background-color: #1D4F91; color: white;'
    '  border: none; border-radius: 5px; font-weight: bold;'
    '}'
    'QPushButton:hover { background-color: #2563EB; }'
)
_BTN_DANGER = (
    'QPushButton {'
    '  background-color: #FFFFFF; color: #DC2626;'
    '  border: 1px solid #FCA5A5; border-radius: 5px;'
    '}'
    'QPushButton:hover { background-color: #FEE2E2; }'
)


class AddEditDialog(QDialog):
    def __init__(self, parent=None, name: str = '', ids: list = None):
        super().__init__(parent)
        self._original_name = name
        edit_mode = bool(name)
        self.setWindowTitle('블로그 ID 목록 편집' if edit_mode else '블로그 ID 목록 추가')
        self.setMinimumWidth(360)
        self.setMinimumHeight(420)
        self._setup_ui(name, ids or [], edit_mode)

    def _setup_ui(self, name: str, ids: list, edit_mode: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel('목록 이름'))
        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText('예: 부산 블로거')
        self.name_input.setStyleSheet(
            'QLineEdit { border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 8px; }'
            'QLineEdit:focus { border-color: #2563EB; }'
        )
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel('블로그 ID (한 줄에 하나씩)'))
        self.ids_input = QTextEdit()
        self.ids_input.setPlaceholderText('blog_id1\nblog_id2\nblog_id3')
        self.ids_input.setStyleSheet(
            'QTextEdit { border: 1px solid #CBD5E1; border-radius: 5px; padding: 6px; }'
            'QTextEdit:focus { border-color: #2563EB; }'
        )
        if ids:
            self.ids_input.setPlainText('\n'.join(ids))
        layout.addWidget(self.ids_input)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton('취소')
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(_BTN_NORMAL)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton('저장' if edit_mode else '추가하기')
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet(_BTN_PRIMARY)
        save_btn.clicked.connect(self._on_save)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, '입력 오류', '목록 이름을 입력해주세요.')
            return

        ids = [
            line.strip()
            for line in self.ids_input.toPlainText().splitlines()
            if line.strip()
        ]
        if not ids:
            QMessageBox.warning(self, '입력 오류', '블로그 ID를 입력해주세요.')
            return

        try:
            if self._original_name and self._original_name != name:
                blog_list_store.delete(self._original_name)
            blog_list_store.save(name, ids)
        except Exception as e:
            QMessageBox.critical(self, '저장 실패', f'서버 저장 중 오류가 발생했습니다.\n{e}')
            return

        self.accept()


class LoadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('블로그 ID 목록 불러오기')
        self.setMinimumWidth(420)
        self.setMinimumHeight(380)
        self.selected_ids: list = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        hint = QLabel('목록 행의 [불러오기]를 클릭하면 블로그 ID가 입력란에 채워집니다.')
        hint.setStyleSheet('color: #6B7280; font-size: 9pt;')
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            'QListWidget { border: 1px solid #CBD5E1; border-radius: 5px; }'
            'QListWidget::item { padding: 0; border-bottom: 1px solid #F3F4F6; }'
        )
        layout.addWidget(self.list_widget)

        close_btn = QPushButton('닫기')
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(_BTN_NORMAL)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

        self._refresh()

    def _refresh(self):
        self.list_widget.clear()
        try:
            lists = blog_list_store.get_all()
        except Exception as e:
            item = QListWidgetItem(f'목록 불러오기 실패: {e}')
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.red)
            self.list_widget.addItem(item)
            return

        if not lists:
            item = QListWidgetItem('저장된 목록이 없습니다.')
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.gray)
            self.list_widget.addItem(item)
            return

        for entry in lists:
            row_widget = self._make_row(entry['name'], entry['ids'])
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, row_widget)

    def _make_row(self, name: str, ids: list) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(6)

        label = QLabel(f'{name}  <span style="color:#9CA3AF;font-size:9pt;">({len(ids)}개)</span>')
        label.setTextFormat(Qt.RichText)
        row.addWidget(label, 1)

        edit_btn = QPushButton('편집')
        edit_btn.setFixedSize(46, 26)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(_BTN_NORMAL)
        edit_btn.clicked.connect(lambda _, n=name, i=ids: self._on_edit(n, i))

        del_btn = QPushButton('삭제')
        del_btn.setFixedSize(46, 26)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(_BTN_DANGER)
        del_btn.clicked.connect(lambda _, n=name: self._on_delete(n))

        load_btn = QPushButton('불러오기')
        load_btn.setFixedSize(72, 26)
        load_btn.setCursor(Qt.PointingHandCursor)
        load_btn.setStyleSheet(_BTN_PRIMARY)
        load_btn.clicked.connect(lambda _, i=ids: self._on_load(i))

        row.addWidget(edit_btn)
        row.addWidget(del_btn)
        row.addWidget(load_btn)
        return widget

    def _on_load(self, ids: list):
        self.selected_ids = ids
        self.accept()

    def _on_edit(self, name: str, ids: list):
        dlg = AddEditDialog(self, name=name, ids=ids)
        if dlg.exec_() == QDialog.Accepted:
            self._refresh()

    def _on_delete(self, name: str):
        reply = QMessageBox.question(
            self,
            '목록 삭제',
            f'"{name}" 목록을 삭제할까요?',
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply == QMessageBox.Ok:
            try:
                blog_list_store.delete(name)
            except Exception as e:
                QMessageBox.critical(self, '삭제 실패', f'서버 삭제 중 오류가 발생했습니다.\n{e}')
                return
            self._refresh()
