import os
import sys
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtWidgets import QApplication, QHeaderView

from ui.right_panel import RightPanel


_APP = QApplication.instance() or QApplication(sys.argv)


class RightPanelTests(unittest.TestCase):
    def test_add_result_shows_blog_id_and_stores_post_url(self):
        panel = RightPanel()

        panel.add_result(
            'blog.naver.com/jslife16',
            68,
            '시청역 점심 맛집 직장인 대표정 서울 시청 회식',
            '시청역 점심',
            0,
            'https://blog.naver.com/jslife16/223456789',
        )

        self.assertEqual(panel.table.item(0, 0).text(), 'jslife16')
        self.assertEqual(
            panel.table.item(0, 0).data(panel.POST_URL_ROLE),
            'https://blog.naver.com/jslife16/223456789',
        )

    def test_columns_are_user_resizable(self):
        panel = RightPanel()
        header = panel.table.horizontalHeader()

        self.assertEqual(header.sectionResizeMode(0), QHeaderView.Interactive)
        self.assertEqual(header.sectionResizeMode(1), QHeaderView.Interactive)
        self.assertEqual(header.sectionResizeMode(2), QHeaderView.Interactive)
        self.assertEqual(header.sectionResizeMode(3), QHeaderView.Interactive)
        self.assertEqual(header.sectionResizeMode(4), QHeaderView.Interactive)

    def test_default_column_widths_fit_within_table_viewport(self):
        panel = RightPanel()
        panel.resize(1500, 800)
        panel.show()
        _APP.processEvents()
        panel._apply_default_column_widths()

        total_width = sum(panel.table.columnWidth(i) for i in range(5))
        self.assertLessEqual(total_width, panel.table.width())
        self.assertGreaterEqual(panel.table.columnWidth(0), 110)
        self.assertGreaterEqual(panel.table.columnWidth(1), 110)
        self.assertGreaterEqual(panel.table.columnWidth(3), 210)
        self.assertGreaterEqual(panel.table.columnWidth(4), 58)
        self.assertGreater(panel.table.columnWidth(2), panel.table.columnWidth(3))

    def test_default_column_widths_match_wide_pc_layout(self):
        panel = RightPanel()
        panel.resize(1780, 900)
        panel.show()
        _APP.processEvents()
        panel._apply_default_column_widths()

        self.assertGreaterEqual(panel.table.columnWidth(0), 120)
        self.assertGreaterEqual(panel.table.columnWidth(1), 200)
        self.assertGreaterEqual(panel.table.columnWidth(3), 250)
        self.assertEqual(panel.table.columnWidth(4), 58)

    def test_summary_shows_top_rank_blog_id(self):
        panel = RightPanel()

        panel.add_result(
            'blog.naver.com/first',
            10,
            '첫 번째 게시글',
            '첫 키워드',
            3,
            'https://blog.naver.com/first/1',
        )
        panel.add_result(
            'blog.naver.com/bestblog',
            20,
            '두 번째 게시글',
            '두 키워드',
            1,
            'https://blog.naver.com/bestblog/2',
        )

        self.assertEqual(panel.top_blog_value.text(), 'bestblog (1위)')


if __name__ == '__main__':
    unittest.main()
