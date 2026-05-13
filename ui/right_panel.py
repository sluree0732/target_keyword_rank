import os
from datetime import datetime

from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
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


def _display_blog_id(blog_url: str) -> str:
    value = blog_url.strip()
    if value.startswith('https://'):
        value = value[len('https://'):]
    elif value.startswith('http://'):
        value = value[len('http://'):]

    value = value.rstrip('/')
    if value.startswith('blog.naver.com/'):
        return value.split('/', 1)[1].split('/', 1)[0]
    return value


def _top_rank_blog_label(results: list) -> str:
    ranked = [item for item in results if item.get('rank', 0) > 0]
    if not ranked:
        return '-'

    best = min(ranked, key=lambda item: item['rank'])
    return f"{_display_blog_id(best['blog_url'])} ({best['rank']}위)"


class RightPanel(QWidget):
    POST_URL_ROLE = Qt.UserRole + 1
    BLOG_URL_ROLE = Qt.UserRole + 2

    def __init__(self):
        super().__init__()
        self._results = []
        self._initial_column_widths_applied = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 20, 20, 18)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title = QLabel('분석 결과')
        title.setFont(QFont('', 15, QFont.Bold))
        title.setStyleSheet('color: #111827;')
        header_row.addWidget(title)
        header_row.addStretch()

        self.download_btn = QPushButton('엑셀 다운로드')
        self.download_btn.setMinimumHeight(38)
        self.download_btn.setMinimumWidth(132)
        self.download_btn.setFont(QFont('', 10, QFont.Bold))
        self.download_btn.setEnabled(False)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #1F7A3A; color: white;'
            '  border-radius: 6px; border: none; padding: 0 16px;'
            '}'
            'QPushButton:hover { background-color: #238447; }'
            'QPushButton:pressed { background-color: #145A2A; }'
            'QPushButton:disabled { background-color: #A7B0BA; }'
        )
        self.download_btn.clicked.connect(self._on_download)
        header_row.addWidget(self.download_btn)
        layout.addLayout(header_row)

        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(
            'QFrame { background: #F8FAFC; border: 1px solid #E5E7EB; border-radius: 8px; }'
            'QLabel { border: none; background: transparent; }'
        )
        summary_layout = QGridLayout(self.summary_frame)
        summary_layout.setContentsMargins(14, 10, 14, 10)
        summary_layout.setHorizontalSpacing(28)
        summary_layout.setVerticalSpacing(2)

        self.total_value = self._make_metric_value()
        self.exposed_value = self._make_metric_value('#166534')
        self.missing_value = self._make_metric_value('#B91C1C')
        self.legend_value = self._make_metric_value('#374151')
        self.top_blog_value = self._make_metric_value('#1D4F91')

        for col, (label, value) in enumerate([
            ('총 결과', self.total_value),
            ('노출 키워드', self.exposed_value),
            ('순위 밖', self.missing_value),
            ('기준', self.legend_value),
            ('상위 블로그', self.top_blog_value),
        ]):
            label_widget = QLabel(label)
            label_widget.setStyleSheet('color: #6B7280; font-size: 9pt;')
            summary_layout.addWidget(label_widget, 0, col)
            summary_layout.addWidget(value, 1, col)

        summary_layout.setColumnStretch(4, 1)
        layout.addWidget(self.summary_frame)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ['블로그', '방문자수', '게시글 제목', '키워드', '순위']
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setStyleSheet(
            'QTableWidget {'
            '  background: white; border: 1px solid #D8DEE8; border-radius: 6px;'
            '  gridline-color: transparent; selection-background-color: #DCEBFF;'
            '  selection-color: #111827;'
            '}'
            'QTableWidget::item { padding: 8px 10px; border-bottom: 1px solid #EEF2F7; }'
            'QTableWidget::item:selected { color: #111827; background: #DCEBFF; }'
            'QTableWidget::item:alternate { background-color: #F9FAFB; }'
            'QTableWidget::item:alternate:selected { color: #111827; background: #DCEBFF; }'
            'QHeaderView::section {'
            '  background-color: #1D4F91; color: white; font-weight: bold;'
            '  padding: 9px 10px; border: none; border-right: 1px solid #2B64AD;'
            '}'
        )

        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        self._apply_default_column_widths()
        QTimer.singleShot(0, self._apply_default_column_widths)
        self.table.cellDoubleClicked.connect(self._open_post_for_row)

        layout.addWidget(self.table, 1)
        self.update_legend(5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initial_column_widths_applied:
            self._apply_default_column_widths()

    def _make_metric_value(self, color='#111827'):
        label = QLabel('0')
        label.setFont(QFont('', 13, QFont.Bold))
        label.setStyleSheet(f'color: {color};')
        return label

    def _apply_default_column_widths(self):
        width = max(self.table.viewport().width(), self.table.width() - 4)
        if width <= 0:
            return

        usable = max(width - 2, 0)
        fixed_widths = {
            0: max(int(usable * 0.07), 110),  # blog id
            1: max(int(usable * 0.12), 110),  # visitor count
            3: max(int(usable * 0.15), 210),  # keyword
            4: max(int(usable * 0.03), 58),   # rank
        }
        minimum_title_width = 300
        minimum_total = sum(fixed_widths.values()) + minimum_title_width

        if minimum_total > usable and usable > minimum_title_width:
            scale = (usable - minimum_title_width) / sum(fixed_widths.values())
            fixed_widths = {
                col: max(40, int(width_value * scale))
                for col, width_value in fixed_widths.items()
            }

        side_total = sum(fixed_widths.values())
        title_width = max(usable - side_total, minimum_title_width if usable >= minimum_total else 120)
        overflow = side_total + title_width - usable
        if overflow > 0:
            title_width = max(80, title_width - overflow)

        self.table.setColumnWidth(0, fixed_widths[0])
        self.table.setColumnWidth(1, fixed_widths[1])
        self.table.setColumnWidth(2, title_width)
        self.table.setColumnWidth(3, fixed_widths[3])
        self.table.setColumnWidth(4, fixed_widths[4])
        self._initial_column_widths_applied = True

    def add_result(
        self,
        blog_url: str,
        visitor_count: int,
        post_title: str,
        keyword: str,
        rank: int,
        post_url: str = '',
    ):
        self._results.append({
            'blog_url': blog_url,
            'visitor_count': visitor_count,
            'post_title': post_title,
            'keyword': keyword,
            'rank': rank,
            'post_url': post_url,
        })

        row = self.table.rowCount()
        self.table.insertRow(row)

        visitor_text = str(visitor_count) if visitor_count > 0 else '-'
        rank_text = f'{rank}위' if rank > 0 else '-'

        blog_id = _display_blog_id(blog_url)
        self.table.setItem(row, 0, self._make_item(blog_id, tooltip=blog_url))
        self.table.setItem(row, 1, self._make_item(visitor_text, Qt.AlignCenter))
        self.table.setItem(row, 2, self._make_item(post_title))
        self.table.setItem(row, 3, self._make_item(keyword))

        rank_item = self._make_item(rank_text, Qt.AlignCenter)
        if rank > 0:
            rank_item.setForeground(QColor('#166534'))
            rank_item.setFont(QFont('', -1, QFont.Bold))
        else:
            rank_item.setForeground(QColor('#B91C1C'))
        self.table.setItem(row, 4, rank_item)
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setData(self.POST_URL_ROLE, post_url)
                item.setData(self.BLOG_URL_ROLE, blog_url)

        self._update_summary()
        self.table.scrollToBottom()
        self.download_btn.setEnabled(True)

    def _make_item(self, text, align=Qt.AlignVCenter | Qt.AlignLeft, tooltip=None):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        item.setToolTip(tooltip or text)
        return item

    def _open_post_for_row(self, row: int, _column: int):
        item = self.table.item(row, 0)
        if not item:
            return

        post_url = item.data(self.POST_URL_ROLE)
        if post_url:
            QDesktopServices.openUrl(QUrl(post_url))

    def flush_last_group(self):
        self._update_summary()

    def update_legend(self, rank_limit: int):
        self.legend_value.setText(f'1~{rank_limit}위')

    def clear_results(self):
        self.table.setRowCount(0)
        self._results.clear()
        self.download_btn.setEnabled(False)
        self._update_summary()

    def _update_summary(self):
        total = len(self._results)
        exposed = sum(1 for item in self._results if item['rank'] > 0)
        missing = total - exposed

        self.total_value.setText(f'{total}건')
        self.exposed_value.setText(f'{exposed}건')
        self.missing_value.setText(f'{missing}건')
        self.top_blog_value.setText(_top_rank_blog_label(self._results))

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
                f'<b>{os.path.basename(filepath)}</b> 파일이 이미 존재합니다.<br>덮어쓰시겠습니까?',
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
