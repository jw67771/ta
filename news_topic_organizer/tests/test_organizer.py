import json
import unittest

from news_topic_organizer import Article, NewsOrganizer


def sample_articles():
    return [
        Article(title="코스피 상승 마감", body="증시가 금리 기대감에 올랐다."),
        Article(title="환율 하락세", body="수출 기업 실적 우려."),
        Article(title="야구 결승전 승리", body="홈런으로 우승을 확정했다."),
        Article(title="알 수 없는 이야기", body="분류할 키워드가 없는 글."),
    ]


class TestNewsOrganizer(unittest.TestCase):
    def setUp(self):
        self.organizer = NewsOrganizer()
        self.groups = self.organizer.organize(sample_articles())

    def test_grouping_counts(self):
        self.assertEqual(len(self.groups["경제"]), 2)
        self.assertEqual(len(self.groups["스포츠"]), 1)
        self.assertEqual(len(self.groups["기타"]), 1)

    def test_topics_sorted_by_count_fallback_last(self):
        topics = list(self.groups.keys())
        self.assertEqual(topics[0], "경제")
        self.assertEqual(topics[-1], "기타")

    def test_markdown_output(self):
        md = self.organizer.to_markdown(self.groups)
        self.assertIn("# 뉴스 기사 주제별 정리", md)
        self.assertIn("총 **4건**", md)
        self.assertIn("## 경제 (2건)", md)
        self.assertIn("코스피 상승 마감", md)

    def test_json_output(self):
        payload = json.loads(self.organizer.to_json(self.groups))
        self.assertEqual(payload["total"], 4)
        topics = {t["topic"]: t["count"] for t in payload["topics"]}
        self.assertEqual(topics["경제"], 2)


if __name__ == "__main__":
    unittest.main()
