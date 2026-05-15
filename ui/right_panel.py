import os
from datetime import datetime

from PyQt5.QtCore import QEvent, QTimer, Qt, QUrl
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabBar,
    QTabWidget,
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


class RightPanel(QWidget):
    POST_URL_ROLE = Qt.UserRole + 1
    BLOG_URL_ROLE = Qt.UserRole + 2
    ITEM_DATA_ROLE = Qt.UserRole + 3

    def __init__(self):
        super().__init__()
        self._tab_results: list = []  # list of list[dict], one per tab
        self._close_btns: list = []
        self._col_resizing: bool = False
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

        self.reset_btn = QPushButton('전체 초기화')
        self.reset_btn.setMinimumHeight(38)
        self.reset_btn.setMinimumWidth(110)
        self.reset_btn.setFont(QFont('', 10))
        self.reset_btn.setEnabled(False)
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #6B7280; color: white;'
            '  border-radius: 6px; border: none; padding: 0 16px;'
            '}'
            'QPushButton:hover { background-color: #4B5563; }'
            'QPushButton:pressed { background-color: #374151; }'
            'QPushButton:disabled { background-color: #D1D5DB; color: #9CA3AF; }'
        )
        self.reset_btn.clicked.connect(self.clear_results)
        header_row.addWidget(self.reset_btn)

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
        for col, (label, value) in enumerate([
            ('총 결과', self.total_value),
            ('노출 키워드', self.exposed_value),
            ('순위 밖', self.missing_value),
            ('기준', self.legend_value),
        ]):
            label_widget = QLabel(label)
            label_widget.setStyleSheet('color: #6B7280; font-size: 9pt;')
            summary_layout.addWidget(label_widget, 0, col)
            summary_layout.addWidget(value, 1, col)

        summary_layout.setColumnStretch(3, 1)
        layout.addWidget(self.summary_frame)

        # 행 선택 상세 정보 바 (선택 시에만 표시)
        self.detail_frame = QFrame()
        self.detail_frame.setVisible(False)
        self.detail_frame.setStyleSheet(
            'QFrame { background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; }'
            'QLabel { border: none; background: transparent; }'
        )
        detail_layout = QHBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(14, 8, 14, 8)
        detail_layout.setSpacing(6)

        sel_label = QLabel('선택')
        sel_label.setStyleSheet('color: #1D4F91; font-weight: bold; font-size: 9pt;')
        detail_layout.addWidget(sel_label)

        sep = QLabel('|')
        sep.setStyleSheet('color: #CBD5E1; font-size: 9pt;')
        detail_layout.addWidget(sep)

        self._detail_blog = self._make_detail_value()
        self._detail_visitor = self._make_detail_value('#6B7280')
        self._detail_title = self._make_detail_value()
        self._detail_keyword = self._make_detail_value('#1D4F91')
        self._detail_rank = self._make_detail_value('#166534')

        for lbl_text, val_widget in [
            ('블로그', self._detail_blog),
            ('방문자수', self._detail_visitor),
            ('게시글', self._detail_title),
            ('키워드', self._detail_keyword),
            ('순위', self._detail_rank),
        ]:
            lbl = QLabel(f'{lbl_text}:')
            lbl.setStyleSheet('color: #6B7280; font-size: 9pt;')
            detail_layout.addWidget(lbl)
            detail_layout.addWidget(val_widget)
            if lbl_text != '순위':
                sp = QLabel('|')
                sp.setStyleSheet('color: #CBD5E1; font-size: 9pt;')
                detail_layout.addWidget(sp)

        detail_layout.addStretch()
        layout.addWidget(self.detail_frame)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.tabBar().setMovable(True)
        self.tab_widget.setStyleSheet(
            'QTabWidget::pane {'
            '  border: 1px solid #D8DEE8; border-top: none;'
            '  background: white;'
            '}'
            'QTabBar::tab {'
            '  background: #EEF2F7; color: #374151;'
            '  border: 1px solid #D8DEE8; border-bottom: none;'
            '  padding: 7px 14px; margin-right: 2px;'
            '  border-top-left-radius: 5px; border-top-right-radius: 5px;'
            '  font-size: 9pt;'
            '}'
            'QTabBar::tab:selected {'
            '  background: white; color: #1D4F91; font-weight: bold;'
            '}'
            'QTabBar::tab:hover:!selected { background: #E2E8F0; }'
        )
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabBar().tabMoved.connect(self._on_tab_moved)
        layout.addWidget(self.tab_widget, 1)

        self.update_legend(5)

    def _make_tab_table(self) -> QTableWidget:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(['블로그', '방문자수', '게시글 제목', '키워드', '순위'])
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setMouseTracking(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)
        table.setProperty('rank_grouped', False)
        table.setStyleSheet(
            'QTableWidget {'
            '  background: white; border: none;'
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
            'QHeaderView::section:hover { background-color: #2563EB; cursor: pointer; }'
        )

        header = table.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setStretchLastSection(False)
        header.setCursor(Qt.PointingHandCursor)
        for col in range(5):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.sectionResized.connect(
            lambda idx, old, new, t=table: self._on_col_resized(idx, old, new, t)
        )

        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        header.sectionClicked.connect(
            lambda col, t=table: self._on_rank_header_clicked(col, t)
        )
        table.cellDoubleClicked.connect(
            lambda row, col, t=table: self._open_post_for_row(row, col, t)
        )
        table.itemSelectionChanged.connect(
            lambda t=table: self._on_row_selected(t)
        )
        QTimer.singleShot(0, lambda t=table: self._apply_default_column_widths(t))
        return table

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for i in range(self.tab_widget.count()):
            self._apply_default_column_widths(self.tab_widget.widget(i))

    def _make_detail_value(self, color='#111827'):
        label = QLabel('')
        label.setFont(QFont('', 9, QFont.Bold))
        label.setStyleSheet(f'color: {color};')
        return label

    def _make_metric_value(self, color='#111827'):
        label = QLabel('0')
        label.setFont(QFont('', 13, QFont.Bold))
        label.setStyleSheet(f'color: {color};')
        return label

    def _on_col_resized(self, logical_index: int, old_size: int, new_size: int, table: QTableWidget):
        if self._col_resizing or logical_index == 2:
            return
        self._col_resizing = True
        total = table.viewport().width()
        used = sum(table.columnWidth(c) for c in range(5) if c != 2)
        table.setColumnWidth(2, max(total - used, 80))
        self._col_resizing = False

    def _apply_default_column_widths(self, table: QTableWidget):
        width = max(table.viewport().width(), table.width() - 4)
        if width <= 0:
            return

        usable = max(width - 2, 0)
        col0 = max(int(usable * 0.08), 90)
        col1 = max(int(usable * 0.09), 80)
        col3 = max(int(usable * 0.20), 160)
        col4 = max(int(usable * 0.05), 76)
        table.setColumnWidth(0, col0)
        table.setColumnWidth(1, col1)
        table.setColumnWidth(3, col3)
        table.setColumnWidth(4, col4)
        table.setColumnWidth(2, max(usable - col0 - col1 - col3 - col4, 80))

    def start_new_analysis(self, grade: int, post_count: int, keyword_count: int, rank_limit: int):
        label = f'키워드 등급{grade}'

        table = self._make_tab_table()
        self._tab_results.append([])
        self.tab_widget.addTab(table, label)

        close_btn = QPushButton('×')
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFont(QFont('', 11))
        close_btn.setStyleSheet(
            'QPushButton { color: #9CA3AF; border: none; background: transparent; padding: 0; }'
            'QPushButton:hover { color: #EF4444; background: #FFE4E4; border-radius: 4px; }'
        )
        close_btn.installEventFilter(self)
        close_btn.clicked.connect(lambda _, b=close_btn: self._close_tab_by_button(b))
        self._close_btns.append(close_btn)
        self.tab_widget.tabBar().setTabButton(
            self.tab_widget.count() - 1,
            QTabBar.RightSide,
            close_btn,
        )

        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        self.reset_btn.setEnabled(True)

    @property
    def result_count(self) -> int:
        return len(self._tab_results[-1]) if self._tab_results else 0

    def add_result(
        self,
        blog_url: str,
        visitor_count: int,
        post_title: str,
        keyword: str,
        rank: int,
        post_url: str = '',
    ):
        if not self._tab_results:
            return

        item = {
            'blog_url': blog_url,
            'visitor_count': visitor_count,
            'post_title': post_title,
            'keyword': keyword,
            'rank': rank,
            'post_url': post_url,
        }
        self._tab_results[-1].append(item)

        last_idx = self.tab_widget.count() - 1
        table = self.tab_widget.widget(last_idx)
        if table is None:
            return

        # 필터 활성 중 새 데이터 추가 시 필터 해제
        if table.property('rank_grouped'):
            table.setProperty('rank_grouped', False)
            table.horizontalHeaderItem(4).setText('순위')

        self._insert_row(table, item)
        self._update_summary()
        table.scrollToBottom()
        self.download_btn.setEnabled(True)

    def _insert_row(self, table: QTableWidget, item: dict, show_post_info: bool = True):
        blog_url = item['blog_url']
        visitor_count = item['visitor_count']
        post_title = item['post_title']
        keyword = item['keyword']
        rank = item['rank']
        post_url = item.get('post_url', '')

        row = table.rowCount()
        table.insertRow(row)

        if show_post_info:
            visitor_text = str(visitor_count) if visitor_count > 0 else '-'
            table.setItem(row, 0, self._make_item(_display_blog_id(blog_url), tooltip=blog_url))
            table.setItem(row, 1, self._make_item(visitor_text, Qt.AlignCenter))
            table.setItem(row, 2, self._make_item(post_title))
        else:
            for col in (0, 1, 2):
                empty = QTableWidgetItem('')
                empty.setBackground(QColor('#F0F4F8'))
                table.setItem(row, col, empty)

        table.setItem(row, 3, self._make_item(keyword))

        rank_text = f'{rank}위' if rank > 0 else '-'
        rank_item = self._make_item(rank_text, Qt.AlignCenter)
        if rank > 0:
            rank_item.setForeground(QColor('#166534'))
            rank_item.setFont(QFont('', -1, QFont.Bold))
        else:
            rank_item.setForeground(QColor('#B91C1C'))
        table.setItem(row, 4, rank_item)

        for col in range(table.columnCount()):
            cell = table.item(row, col)
            if cell:
                cell.setData(self.POST_URL_ROLE, post_url)
                cell.setData(self.BLOG_URL_ROLE, blog_url)
                cell.setData(self.ITEM_DATA_ROLE, item)

    def _make_item(self, text, align=Qt.AlignVCenter | Qt.AlignLeft, tooltip=None):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        item.setToolTip(tooltip or text)
        return item

    def _open_post_for_row(self, row: int, _column: int, table: QTableWidget):
        item = table.item(row, 0)
        if not item:
            return
        post_url = item.data(self.POST_URL_ROLE)
        if post_url:
            QDesktopServices.openUrl(QUrl(post_url))

    def _close_tab_by_button(self, btn: QPushButton):
        bar = self.tab_widget.tabBar()
        for i in range(bar.count()):
            if bar.tabButton(i, QTabBar.RightSide) is btn:
                self._close_tab(i)
                return

    def _close_tab(self, index: int):
        btn = self.tab_widget.tabBar().tabButton(index, QTabBar.RightSide)
        self._close_btns = [b for b in self._close_btns if b is not btn]
        self._tab_results.pop(index)
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.download_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)
        self._update_summary()

    def _on_tab_moved(self, from_idx: int, to_idx: int):
        self._tab_results.insert(to_idx, self._tab_results.pop(from_idx))

    def _on_rank_header_clicked(self, col: int, table: QTableWidget):
        if col != 4:
            return
        idx = self.tab_widget.indexOf(table)
        if idx < 0 or idx >= len(self._tab_results):
            return

        active = not (table.property('rank_grouped') or False)
        table.setProperty('rank_grouped', active)
        self._refresh_table_view(table, self._tab_results[idx])

    def _get_rank_grouped_rows(self, results: list) -> list:
        seen_blogs: list = []
        blog_posts: dict = {}   # blog_url -> [post_key, ...]
        post_items: dict = {}   # (blog_url, post_title) -> [items]

        for item in results:
            if item['rank'] <= 0:
                continue
            blog = item['blog_url']
            key = (blog, item['post_title'])

            if blog not in seen_blogs:
                seen_blogs.append(blog)
                blog_posts[blog] = []

            if key not in post_items:
                post_items[key] = []
                blog_posts[blog].append(key)

            post_items[key].append(item)

        rows = []
        for blog in seen_blogs:
            for key in blog_posts.get(blog, []):
                for i, item in enumerate(sorted(post_items[key], key=lambda x: x['rank'])):
                    rows.append({**item, '_show_post_info': i == 0})

        return rows

    def _refresh_table_view(self, table: QTableWidget, results: list):
        active = table.property('rank_grouped') or False
        header_item = table.horizontalHeaderItem(4)
        if header_item:
            header_item.setText('순위 ↑' if active else '순위')

        table.setRowCount(0)

        if active:
            for row_data in self._get_rank_grouped_rows(results):
                self._insert_row(table, row_data, row_data.get('_show_post_info', True))
        else:
            for item in results:
                self._insert_row(table, item)

    def flush_last_group(self):
        self._update_summary()

    def update_legend(self, rank_limit: int):
        self.legend_value.setText(f'1~{rank_limit}위')

    def clear_results(self):
        self._close_btns.clear()
        self.tab_widget.clear()
        self._tab_results.clear()
        self.detail_frame.setVisible(False)
        self.download_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self._update_summary()

    def _on_row_selected(self, table: QTableWidget):
        row = table.currentRow()
        if row < 0:
            self.detail_frame.setVisible(False)
            return

        cell = table.item(row, 0)
        if not cell:
            self.detail_frame.setVisible(False)
            return

        item = cell.data(self.ITEM_DATA_ROLE)
        if not item:
            self.detail_frame.setVisible(False)
            return

        self._detail_blog.setText(_display_blog_id(item['blog_url']))
        visitor = str(item['visitor_count']) if item['visitor_count'] > 0 else '-'
        self._detail_visitor.setText(visitor)
        self._detail_title.setText(item['post_title'])
        self._detail_keyword.setText(item['keyword'])
        rank = f"{item['rank']}위" if item['rank'] > 0 else '-'
        self._detail_rank.setText(rank)
        color = '#166534' if item['rank'] > 0 else '#B91C1C'
        self._detail_rank.setStyleSheet(f'color: {color}; font-weight: bold; font-size: 9pt;')
        self.detail_frame.setVisible(True)

    def eventFilter(self, obj, event):
        if obj in self._close_btns:
            if event.type() == QEvent.Enter:
                obj.setFixedSize(24, 24)
                obj.setFont(QFont('', 13))
            elif event.type() == QEvent.Leave:
                obj.setFixedSize(20, 20)
                obj.setFont(QFont('', 11))
        return super().eventFilter(obj, event)

    def _on_tab_changed(self, index: int):
        self.detail_frame.setVisible(False)
        self._update_summary()
        has_results = 0 <= index < len(self._tab_results) and bool(self._tab_results[index])
        self.download_btn.setEnabled(has_results)

    def _update_summary(self):
        idx = self.tab_widget.currentIndex()
        results = self._tab_results[idx] if 0 <= idx < len(self._tab_results) else []

        total = len(results)
        exposed = sum(1 for item in results if item['rank'] > 0)
        missing = total - exposed

        self.total_value.setText(f'{total}건')
        self.exposed_value.setText(f'{exposed}건')
        self.missing_value.setText(f'{missing}건')

    def _on_download(self):
        idx = self.tab_widget.currentIndex()
        if idx < 0 or idx >= len(self._tab_results):
            return
        results = self._tab_results[idx]

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
            export_to_excel(results, filepath)
            count = len(results)
            filename = os.path.basename(filepath)
            msg = QMessageBox(self)
            msg.setWindowTitle('저장 완료')
            msg.setIcon(QMessageBox.Information)
            msg.setText(f'<b>{filename}</b><br>총 {count}건 저장되었습니다.')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        except Exception as e:
            QMessageBox.warning(self, '저장 실패', str(e))
