import unittest

from news_topic_organizer import Article, TopicClassifier


class TestTopicClassifier(unittest.TestCase):
    def setUp(self):
        self.clf = TopicClassifier()

    def test_economy_article(self):
        article = Article(
            title="코스피 급등, 금리 인하 기대감",
            body="증시가 상승했다. 외국인 투자가 늘고 환율은 안정세를 보였다.",
        )
        self.assertEqual(self.clf.classify(article).topic, "경제")

    def test_sports_article(self):
        article = Article(
            title="손흥민 결승골, 팀 우승 확정",
            body="축구 리그 결승에서 극적인 골이 터졌다.",
        )
        self.assertEqual(self.clf.classify(article).topic, "스포츠")

    def test_tech_article_english(self):
        article = Article(
            title="AI chip startup raises funding",
            body="The semiconductor company develops machine learning hardware.",
        )
        self.assertEqual(self.clf.classify(article).topic, "IT/과학")

    def test_fallback_topic(self):
        article = Article(title="오늘 점심 뭐 먹지", body="메뉴 고민.")
        self.assertEqual(self.clf.classify(article).topic, "기타")

    def test_title_weight_beats_body(self):
        # 제목의 키워드(가중치 3배)가 본문 키워드 1개보다 우선한다
        article = Article(title="대통령 국회 연설", body="주가 언급.")
        self.assertEqual(self.clf.classify(article).topic, "정치")

    def test_english_word_boundary(self):
        # 'AI'가 'said' 같은 단어 내부에 매칭되면 안 된다
        article = Article(title="He said hello", body="plain daily note")
        scores = self.clf.score(article)
        self.assertEqual(scores["IT/과학"], 0.0)

    def test_custom_topics(self):
        clf = TopicClassifier(topics={"날씨": ["폭염", "장마", "태풍"]})
        article = Article(title="태풍 북상, 전국 장마 시작", body="")
        self.assertEqual(clf.classify(article).topic, "날씨")

    def test_classify_all(self):
        articles = [
            Article(title="코스피 상승", body="증시 호조"),
            Article(title="야구 결승", body="홈런 두 방"),
        ]
        results = self.clf.classify_all(articles)
        self.assertEqual([r.topic for r in results], ["경제", "스포츠"])


if __name__ == "__main__":
    unittest.main()
