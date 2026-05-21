import os
from datetime import datetime

from PyQt5.QtCore import QEvent, QItemSelectionModel, QThread, QTimer, Qt, QUrl, pyqtSignal
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
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.excel_exporter import export_to_excel


class _TitleReadOnlyDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setReadOnly(True)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(index.data() or '')

    def setModelData(self, editor, model, index):
        pass  # 원본 데이터 변경 차단


class _ReCheckWorker(QThread):
    row_done = pyqtSignal(int, int)  # row_index, rank
    all_done = pyqtSignal()

    def __init__(self, tasks: list, rank_limit: int):
        super().__init__()
        self._tasks = tasks  # list of (row_index, post_url, keyword)
        self._rank_limit = rank_limit

    def run(self):
        from core.rank_checker import check_rank, create_session
        session = create_session()
        for row_idx, post_url, keyword in self._tasks:
            try:
                rank = check_rank(keyword, post_url, session, self._rank_limit)
            except Exception:
                rank = 0
            self.row_done.emit(row_idx, rank)
        self.all_done.emit()


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
        self._rank_limit: int = 30
        self._recheck_worker: _ReCheckWorker | None = None
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
        self.reset_btn.setFont(QFont('', 10))
        self.reset_btn.setEnabled(False)
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #6B7280; color: white;'
            '  border-radius: 6px; border: none; padding: 0 10px;'
            '}'
            'QPushButton:hover { background-color: #4B5563; }'
            'QPushButton:pressed { background-color: #374151; }'
            'QPushButton:disabled { background-color: #D1D5DB; color: #9CA3AF; }'
        )
        self.reset_btn.clicked.connect(self.clear_results)
        header_row.addWidget(self.reset_btn)

        self.download_btn = QPushButton('엑셀 다운로드')
        self.download_btn.setMinimumHeight(38)
        self.download_btn.setFont(QFont('', 10, QFont.Bold))
        self.download_btn.setEnabled(False)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #1F7A3A; color: white;'
            '  border-radius: 6px; border: none; padding: 0 10px;'
            '}'
            'QPushButton:hover { background-color: #238447; }'
            'QPushButton:pressed { background-color: #145A2A; }'
            'QPushButton:disabled { background-color: #A7B0BA; }'
        )
        self.download_btn.clicked.connect(self._on_download)
        header_row.addWidget(self.download_btn)

        self.recheck_btn = QPushButton('순위 재확인')
        self.recheck_btn.setMinimumHeight(38)
        self.recheck_btn.setFont(QFont('', 10))
        self.recheck_btn.setEnabled(False)
        self.recheck_btn.setCursor(Qt.PointingHandCursor)
        self.recheck_btn.setStyleSheet(
            'QPushButton {'
            '  background-color: #1D4F91; color: white;'
            '  border-radius: 6px; border: none; padding: 0 10px;'
            '}'
            'QPushButton:hover { background-color: #2563EB; }'
            'QPushButton:pressed { background-color: #1E3A6E; }'
            'QPushButton:disabled { background-color: #D1D5DB; color: #9CA3AF; }'
        )
        self.recheck_btn.clicked.connect(self._on_recheck_clicked)
        header_row.addWidget(self.recheck_btn)

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
        self.detail_frame.setVisible(True)
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
        for w in (self._detail_blog, self._detail_visitor, self._detail_title,
                  self._detail_keyword, self._detail_rank):
            w.setText('-')

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

    # 열 인덱스 상수
    COL_BLOG = 0
    COL_VISITOR = 1
    COL_TITLE = 2
    COL_LINK = 3
    COL_KEYWORD = 4
    COL_RANK = 5

    def _make_tab_table(self) -> QTableWidget:
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(['블로그', '방문자수', '게시글 제목', 'URL', '키워드', '순위'])
        table.setEditTriggers(QTableWidget.DoubleClicked)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setMouseTracking(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)
        table.setProperty('rank_mode', 0)
        table.setProperty('_cur_blog', '')
        table.setProperty('_cur_blog_start', -1)
        table.setStyleSheet(
            'QTableWidget {'
            '  background: white; border: none;'
            '  gridline-color: transparent; selection-background-color: #DCEBFF;'
            '  selection-color: #111827;'
            '}'
            'QTableWidget::item { padding: 8px 10px; border-bottom: 1px solid #EEF2F7; }'
            'QTableWidget::item:selected { color: #111827; background: #DCEBFF; }'
            'QHeaderView::section {'
            '  background-color: #1D4F91; color: white; font-weight: bold;'
            '  padding: 9px 10px; border: none; border-right: 1px solid #2B64AD;'
            '}'
            'QHeaderView::section:hover { background-color: #2563EB; cursor: pointer; }'
        )

        header = table.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setStretchLastSection(True)
        header.setCursor(Qt.PointingHandCursor)
        for col in (self.COL_BLOG, self.COL_VISITOR, self.COL_TITLE, self.COL_KEYWORD):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.setSectionResizeMode(self.COL_LINK, QHeaderView.Fixed)

        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        header.sectionClicked.connect(
            lambda col, t=table: self._on_rank_header_clicked(col, t)
        )
        table.cellClicked.connect(
            lambda row, col, t=table: self._on_cell_clicked(row, col, t)
        )
        table.itemSelectionChanged.connect(
            lambda t=table: self._on_row_selected(t)
        )
        table.itemChanged.connect(
            lambda item, t=table: self._on_keyword_cell_changed(item, t)
        )
        table.setItemDelegateForColumn(self.COL_TITLE, _TitleReadOnlyDelegate(table))
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

    def _apply_default_column_widths(self, table: QTableWidget):
        width = max(table.viewport().width(), table.width() - 4)
        if width <= 0:
            return

        usable = max(width - 2, 0)
        col0 = max(int(usable * 0.09), 120)
        col1 = max(int(usable * 0.08), 72)
        col3_link = 44
        col4 = max(int(usable * 0.19), 140)
        col4_reserved = max(int(usable * 0.08), 65)
        col2 = max(usable - col0 - col1 - col3_link - col4 - col4_reserved, 80)
        table.setColumnWidth(0, col0)
        table.setColumnWidth(1, col1)
        table.setColumnWidth(2, col2)
        table.setColumnWidth(3, col3_link)
        table.setColumnWidth(4, col4)

    def start_new_analysis(self, grade: int, post_count: int, keyword_count: int, rank_limit: int):
        self._rank_limit = rank_limit
        label = f'키워드 등급{grade}'

        table = self._make_tab_table()
        self._tab_results.append([])
        self.tab_widget.addTab(table, label)

        close_btn = QPushButton('×')
        close_btn.setFixedSize(22, 22)
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
        if (table.property('rank_mode') or 0) != 0:
            table.setProperty('rank_mode', 0)
            table.horizontalHeaderItem(5).setText('순위')

        self._insert_row(table, item)
        if table.rowCount() == 1:
            table.selectRow(0)
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
        table.blockSignals(True)
        table.insertRow(row)

        if show_post_info:
            visitor_text = str(visitor_count) if visitor_count > 0 else '-'
            table.setItem(row, 0, self._make_item(_display_blog_id(blog_url), tooltip=blog_url))
            table.setItem(row, 1, self._make_item(visitor_text, Qt.AlignCenter))
            title_item = self._make_item(post_title)
            title_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            table.setItem(row, 2, title_item)
        else:
            for col in (0, 1, 2):
                empty = QTableWidgetItem('')
                empty.setFlags(Qt.ItemIsEnabled)
                empty.setBackground(QColor('#F0F4F8'))
                table.setItem(row, col, empty)

        if post_url:
            link_item = QTableWidgetItem('⧉')
            link_item.setTextAlignment(Qt.AlignCenter)
            link_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            link_item.setForeground(QColor('#2563EB'))
            link_item.setToolTip('게시글 열기')
        else:
            link_item = QTableWidgetItem('')
            link_item.setFlags(Qt.ItemIsEnabled)
        table.setItem(row, self.COL_LINK, link_item)

        kw_item = self._make_item(keyword)
        kw_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        table.setItem(row, self.COL_KEYWORD, kw_item)

        rank_text = f'{rank}위' if rank > 0 else '-'
        rank_item = self._make_item(rank_text, Qt.AlignCenter)
        rank_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if rank > 0:
            rank_item.setForeground(QColor('#166534'))
            rank_item.setFont(QFont('', -1, QFont.Bold))
        else:
            rank_item.setForeground(QColor('#B91C1C'))
        table.setItem(row, self.COL_RANK, rank_item)

        for col in range(table.columnCount()):
            cell = table.item(row, col)
            if cell:
                cell.setData(self.POST_URL_ROLE, post_url)
                cell.setData(self.BLOG_URL_ROLE, blog_url)
                cell.setData(self.ITEM_DATA_ROLE, item)

        alt_bg = QColor('#F9FAFB') if row % 2 else QColor('#FFFFFF')

        if show_post_info:
            cur_blog = table.property('_cur_blog') or ''
            cur_start = table.property('_cur_blog_start')
            if cur_start is None:
                cur_start = -1
            is_same_blog = blog_url == cur_blog and cur_start >= 0
            group_bg = QColor('#EFF6FF')
            if is_same_blog:
                span = row - cur_start + 1
                table.setSpan(cur_start, 0, span, 1)
                table.setSpan(cur_start, 1, span, 1)
                for col in (0, 1):
                    cell = table.item(row, col)
                    if cell:
                        cell.setText('')
                        cell.setToolTip('')
                        cell.setFlags(Qt.ItemIsEnabled)
                        cell.setBackground(group_bg)
            else:
                table.setProperty('_cur_blog', blog_url)
                table.setProperty('_cur_blog_start', row)
                for col in (0, 1):
                    cell = table.item(row, col)
                    if cell:
                        cell.setFlags(Qt.ItemIsEnabled)
                        cell.setBackground(group_bg)
                cell0 = table.item(row, 0)
                if cell0:
                    cell0.setTextAlignment(Qt.AlignTop | Qt.AlignHCenter)
                cell1 = table.item(row, 1)
                if cell1:
                    cell1.setTextAlignment(Qt.AlignTop | Qt.AlignHCenter)
            for col in (2, 3, 4, 5):
                cell = table.item(row, col)
                if cell:
                    cell.setBackground(alt_bg)
        else:
            table.setProperty('_cur_blog', '')
            table.setProperty('_cur_blog_start', -1)
            for col in (3, 4, 5):
                cell = table.item(row, col)
                if cell:
                    cell.setBackground(alt_bg)

        table.blockSignals(False)

    def _make_item(self, text, align=Qt.AlignVCenter | Qt.AlignLeft, tooltip=None):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        item.setToolTip(tooltip or text)
        return item

    def _on_cell_clicked(self, row: int, col: int, table: QTableWidget):
        if col == self.COL_LINK:
            item = table.item(row, 0)
            if item:
                post_url = item.data(self.POST_URL_ROLE)
                if post_url:
                    QDesktopServices.openUrl(QUrl(post_url))
            return
        is_rechecking = self._recheck_worker is not None and self._recheck_worker.isRunning()
        selected = table.selectionModel().selectedRows()
        self.recheck_btn.setEnabled(len(selected) > 0 and not is_rechecking)

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
        if col != 5:
            return
        idx = self.tab_widget.indexOf(table)
        if idx < 0 or idx >= len(self._tab_results):
            return

        current = table.property('rank_mode') or 0
        table.setProperty('rank_mode', (current + 1) % 3)
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

    def _get_rank_sorted_rows(self, results: list) -> list:
        seen_blogs: list = []
        blog_items: dict = {}

        for item in results:
            blog = item['blog_url']
            if blog not in seen_blogs:
                seen_blogs.append(blog)
                blog_items[blog] = {'ranked': [], 'unranked': []}
            if item['rank'] > 0:
                blog_items[blog]['ranked'].append(item)
            else:
                blog_items[blog]['unranked'].append(item)

        rows = []
        for blog in seen_blogs:
            ranked = sorted(blog_items[blog]['ranked'], key=lambda x: x['rank'])
            rows.extend(ranked)
            rows.extend(blog_items[blog]['unranked'])
        return rows

    def _refresh_table_view(self, table: QTableWidget, results: list):
        mode = table.property('rank_mode') or 0
        header_item = table.horizontalHeaderItem(5)
        if header_item:
            header_texts = ['순위', '순위 ↑', '순위만']
            header_item.setText(header_texts[mode])

        table.setProperty('_cur_blog', '')
        table.setProperty('_cur_blog_start', -1)
        table.setRowCount(0)

        if mode == 1:
            for item in self._get_rank_sorted_rows(results):
                self._insert_row(table, item)
        elif mode == 2:
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
        self._clear_detail_bar()
        self.download_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self._update_summary()

    def _on_row_selected(self, table: QTableWidget):
        selected_rows = table.selectionModel().selectedRows()
        is_rechecking = self._recheck_worker is not None and self._recheck_worker.isRunning()
        self.recheck_btn.setEnabled(len(selected_rows) > 0 and not is_rechecking)

        row = table.currentRow()
        if row < 0 or not selected_rows:
            self._clear_detail_bar()
            return

        cell = table.item(row, 0)
        if not cell:
            self._clear_detail_bar()
            return

        item = cell.data(self.ITEM_DATA_ROLE)
        if not item:
            self._clear_detail_bar()
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

    def _clear_detail_bar(self):
        for w in (self._detail_blog, self._detail_visitor, self._detail_title,
                  self._detail_keyword, self._detail_rank):
            w.setText('-')
        self._detail_rank.setStyleSheet('color: #166534; font-weight: bold; font-size: 9pt;')

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    def _on_tab_changed(self, index: int):
        self._clear_detail_bar()
        self._update_summary()
        has_results = 0 <= index < len(self._tab_results) and bool(self._tab_results[index])
        self.download_btn.setEnabled(has_results)
        table = self.tab_widget.widget(index) if 0 <= index < self.tab_widget.count() else None
        is_rechecking = self._recheck_worker is not None and self._recheck_worker.isRunning()
        if table and not is_rechecking:
            selected = table.selectionModel().selectedRows()
            self.recheck_btn.setEnabled(len(selected) > 0)
        else:
            self.recheck_btn.setEnabled(False)

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

    def _on_keyword_cell_changed(self, changed_item: QTableWidgetItem, table: QTableWidget):
        if changed_item.column() != 4:
            return
        if not (changed_item.flags() & Qt.ItemIsEditable):
            return
        row = changed_item.row()
        cell0 = table.item(row, 0)
        if not cell0:
            return
        item = cell0.data(self.ITEM_DATA_ROLE)
        if item:
            item['keyword'] = changed_item.text().strip()
        table.blockSignals(True)
        changed_item.setForeground(QColor('#1D4F91'))
        changed_item.setFont(QFont('', -1, QFont.Bold))
        table.blockSignals(False)
        table.selectionModel().select(
            table.model().index(row, 0),
            QItemSelectionModel.Select | QItemSelectionModel.Rows,
        )

    def _on_recheck_clicked(self):
        idx = self.tab_widget.currentIndex()
        if idx < 0:
            return
        table = self.tab_widget.widget(idx)
        if not table:
            return

        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return

        tasks = []
        for index in selected_rows:
            row = index.row()
            kw_item = table.item(row, 4)
            if not kw_item:
                continue
            keyword = kw_item.text().strip()
            if not keyword:
                continue
            cell0 = table.item(row, 0)
            if not cell0:
                continue
            post_url = cell0.data(self.POST_URL_ROLE) or ''
            if not post_url:
                continue
            item = cell0.data(self.ITEM_DATA_ROLE)
            if item:
                item['keyword'] = keyword
            tasks.append((row, post_url, keyword))

        if not tasks:
            return

        self.recheck_btn.setEnabled(False)
        self.recheck_btn.setText('확인 중...')

        self._recheck_worker = _ReCheckWorker(tasks, self._rank_limit)
        self._recheck_worker.row_done.connect(
            lambda row, rank, t=table: self._on_recheck_row_done(t, row, rank)
        )
        self._recheck_worker.all_done.connect(self._on_recheck_finished)
        self._recheck_worker.start()

    def _on_recheck_row_done(self, table: QTableWidget, row: int, rank: int):
        cell0 = table.item(row, 0)
        if cell0:
            item = cell0.data(self.ITEM_DATA_ROLE)
            if item:
                item['rank'] = rank

        rank_cell = table.item(row, 5)
        if rank_cell:
            table.blockSignals(True)
            rank_text = f'{rank}위' if rank > 0 else '-'
            rank_cell.setText(rank_text)
            if rank > 0:
                rank_cell.setForeground(QColor('#166534'))
                rank_cell.setFont(QFont('', -1, QFont.Bold))
            else:
                rank_cell.setForeground(QColor('#B91C1C'))
                rank_cell.setFont(QFont('', -1, QFont.Normal))
            kw_cell = table.item(row, 4)
            if kw_cell:
                kw_cell.setForeground(QColor('#111827'))
                kw_cell.setFont(QFont('', -1, QFont.Normal))
            table.blockSignals(False)
        table.selectionModel().select(
            table.model().index(row, 0),
            QItemSelectionModel.Deselect | QItemSelectionModel.Rows,
        )

        self._update_summary()

    def _on_recheck_finished(self):
        self.recheck_btn.setText('순위 재확인')
        idx = self.tab_widget.currentIndex()
        if idx >= 0:
            table = self.tab_widget.widget(idx)
            if table:
                selected = table.selectionModel().selectedRows()
                self.recheck_btn.setEnabled(len(selected) > 0)
