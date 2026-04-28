import os
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.excel_exporter import export_to_excel


class RightPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._results = []
        self._group_start_row = -1
        self._group_key = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 20, 20, 20)

        title = QLabel('분석 결과')
        title.setFont(QFont('', 13, QFont.Bold))
        layout.addWidget(title)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background: #E0E0E0;')
        layout.addWidget(sep)

        # 범례 (분석 시작 시 동적 갱신)
        self.legend = QLabel('분석을 시작하면 범례가 표시됩니다.')
        self.legend.setTextFormat(Qt.RichText)
        self.legend.setStyleSheet('font-size: 9pt; color: #9E9E9E;')
        layout.addWidget(self.legend)

        # 테이블 — 5컬럼
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ['블로그 주소', '오늘 방문자', '게시글 제목', '키워드', '순위']
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            'QTableWidget { border: 1px solid #E0E0E0; }'
            'QTableWidget::item { padding: 6px; }'
            'QHeaderView::section {'
            '  background-color: #1565C0; color: white;'
            '  font-weight: bold; padding: 8px; border: none;'
            '}'
            'QTableWidget::item:alternate { background-color: #F8F9FA; }'
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)

        # 다운로드 버튼
        self.download_btn = QPushButton('엑셀 다운로드')
        self.download_btn.setMinimumHeight(40)
        self.download_btn.setFont(QFont('', 10, QFont.Bold))
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #2E7D32; color: white;'
            '  border-radius: 6px; border: none;'
            '}'
            'QPushButton:hover { background-color: #388E3C; }'
            'QPushButton:pressed { background-color: #1B5E20; }'
            'QPushButton:disabled { background-color: #90A4AE; }'
        )
        self.download_btn.clicked.connect(self._on_download)
        layout.addWidget(self.download_btn)

    def add_result(
        self,
        blog_url: str,
        visitor_count: int,
        post_title: str,
        keyword: str,
        rank: int,
    ):
        self._results.append({
            'blog_url': blog_url,
            'visitor_count': visitor_count,
            'post_title': post_title,
            'keyword': keyword,
            'rank': rank,
        })

        row = self.table.rowCount()  # insertRow 전에 확보

        post_key = (blog_url, post_title)
        if post_key != self._group_key:
            self._flush_span(row)    # 새 행 삽입 전에 이전 그룹 span 확정
            self._group_key = post_key
            self._group_start_row = row

        self.table.insertRow(row)    # flush 이후에 삽입

        rank_text = f'{rank}위' if rank > 0 else '-'
        visitor_text = str(visitor_count) if visitor_count > 0 else '-'

        def make_item(text, align=Qt.AlignVCenter | Qt.AlignLeft):
            item = QTableWidgetItem(text)
            item.setTextAlignment(align)
            return item

        self.table.setItem(row, 0, make_item(blog_url))
        self.table.setItem(row, 1, make_item(visitor_text, Qt.AlignCenter))
        self.table.setItem(row, 2, make_item(post_title))

        self.table.setItem(row, 3, make_item(keyword))

        rank_item = make_item(rank_text, Qt.AlignCenter)
        if rank > 0:
            rank_item.setForeground(QColor('#1B5E20'))
            rank_item.setFont(QFont('', -1, QFont.Bold))
        else:
            rank_item.setForeground(QColor('#B71C1C'))

        self.table.setItem(row, 4, rank_item)
        self.table.scrollToBottom()
        self.download_btn.setEnabled(True)

    def _flush_span(self, end_row: int):
        if self._group_start_row < 0:
            return
        span = end_row - self._group_start_row
        if span <= 1:
            return
        for col in (0, 1, 2):
            self.table.setSpan(self._group_start_row, col, span, 1)
            item = self.table.item(self._group_start_row, col)
            if item:
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)

    def flush_last_group(self):
        self._flush_span(self.table.rowCount())

    def update_legend(self, rank_limit: int):
        self.legend.setStyleSheet('font-size: 9pt;')
        self.legend.setText(
            f'■ <span style="color:#1B5E20;font-weight:bold;">1~{rank_limit}위</span>'
            '&nbsp;&nbsp;&nbsp;'
            f'■ <span style="color:#B71C1C;font-weight:bold;">순위 밖 (-)</span>'
        )

    def clear_results(self):
        self.table.setRowCount(0)
        self._results.clear()
        self._group_start_row = -1
        self._group_key = None
        self.download_btn.setEnabled(False)

    def _on_download(self):
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        default_name = f'키워드분석결과_{timestamp}.xlsx'
        filepath, _ = QFileDialog.getSaveFileName(
            self, '엑셀 저장', default_name, 'Excel Files (*.xlsx)'
        )
        if not filepath:
            return

        if os.path.exists(filepath):
            reply = QMessageBox.question(
                self, '파일 덮어쓰기',
                f'<b>{os.path.basename(filepath)}</b> 파일이 이미 존재합니다.<br>덮어쓰겠습니까?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        try:
            export_to_excel(self._results, filepath)
            count = len(self._results)
            filename = os.path.basename(filepath)
            msg = QMessageBox(self)
            msg.setWindowTitle('저장 완료')
            msg.setIcon(QMessageBox.Information)
            msg.setText(f'<b>{filename}</b><br>총 {count}건 저장되었습니다.')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        except Exception as e:
            QMessageBox.warning(self, '저장 실패', str(e))
