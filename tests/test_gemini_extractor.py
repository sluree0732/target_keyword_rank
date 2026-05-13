import unittest

from core import gemini_extractor


class GeminiExtractorTests(unittest.TestCase):
    def test_build_prompt_uses_indexed_titles_and_search_keyword_rules(self):
        prompt = gemini_extractor._build_prompt(
            ['해운대 장어구이 맛집 후기', '서면 피부관리샵 추천'],
            grade=3,
            count=2,
        )

        self.assertIn('1. 해운대 장어구이 맛집 후기', prompt)
        self.assertIn('2. 서면 피부관리샵 추천', prompt)
        self.assertIn('네이버 블로그 검색 순위 확인용', prompt)
        self.assertIn('제목에 없는 지역명, 브랜드명, 업종을 추론하지 마', prompt)
        self.assertIn('"index"', prompt)

    def test_normalize_results_maps_by_index_not_response_order(self):
        titles = ['해운대 장어구이 맛집 후기', '서면 피부관리샵 추천']
        data = {
            'results': [
                {'index': 2, 'keywords': ['서면 피부관리', '피부관리샵']},
                {'index': 1, 'keywords': ['해운대 장어구이', '장어구이 맛집']},
            ]
        }

        mapping = gemini_extractor._normalize_keyword_results(data, titles, count=2)

        self.assertEqual(
            mapping,
            {
                '해운대 장어구이 맛집 후기': ['해운대 장어구이', '장어구이 맛집'],
                '서면 피부관리샵 추천': ['서면 피부관리', '피부관리샵'],
            },
        )

    def test_normalize_results_filters_duplicates_and_bad_keywords(self):
        titles = ['해운대 장어구이 맛집 후기']
        data = {
            'results': [
                {
                    'index': 1,
                    'keywords': [
                        '해운대 장어구이',
                        '해운대 장어구이',
                        '',
                        '맛',
                        '서울 맛집',
                        '장어구이 맛집',
                    ],
                },
            ]
        }

        mapping = gemini_extractor._normalize_keyword_results(data, titles, count=3)

        self.assertEqual(
            mapping['해운대 장어구이 맛집 후기'],
            ['해운대 장어구이', '장어구이 맛집'],
        )


if __name__ == '__main__':
    unittest.main()
