import json
import tempfile
import unittest
from pathlib import Path

from news_topic_organizer.loader import load_file, load_path, load_text


class TestLoader(unittest.TestCase):
    def test_load_text_single(self):
        articles = load_text("제목입니다\n본문 첫 줄.\n본문 둘째 줄.")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "제목입니다")
        self.assertIn("둘째 줄", articles[0].body)

    def test_load_text_multiple_with_separator(self):
        text = "기사1 제목\n기사1 본문\n---\n기사2 제목\n기사2 본문"
        articles = load_text(text)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[1].title, "기사2 제목")

    def test_load_json_file(self):
        data = [
            {"title": "제목A", "body": "본문A", "date": "2026-01-01"},
            {"title": "제목B", "content": "본문B"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "news.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            articles = load_file(path)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].date, "2026-01-01")
        self.assertEqual(articles[1].body, "본문B")

    def test_load_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.txt").write_text("제목1\n본문1", encoding="utf-8")
            (Path(tmp) / "b.json").write_text(
                json.dumps({"title": "제목2", "body": "본문2"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (Path(tmp) / "ignore.md").write_text("무시됨", encoding="utf-8")
            articles = load_path(tmp)
        self.assertEqual(len(articles), 2)


if __name__ == "__main__":
    unittest.main()
