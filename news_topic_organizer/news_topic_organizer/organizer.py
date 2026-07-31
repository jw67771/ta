"""분류 결과를 주제별로 묶어 리포트를 생성한다."""

import json
from collections import OrderedDict
from typing import Dict, Iterable, List, Optional

from .classifier import TopicClassifier
from .models import Article, ClassifiedArticle

SNIPPET_LENGTH = 120


def _snippet(text: str, length: int = SNIPPET_LENGTH) -> str:
    text = " ".join(text.split())
    if len(text) <= length:
        return text
    return text[:length].rstrip() + "…"


class NewsOrganizer:
    """기사들을 분류하고 주제별로 정리한다."""

    def __init__(self, classifier: Optional[TopicClassifier] = None):
        self.classifier = classifier or TopicClassifier()

    def organize(self, articles: Iterable[Article]) -> "OrderedDict[str, List[ClassifiedArticle]]":
        """기사를 분류해 주제 → 기사 목록 매핑을 만든다.

        주제는 기사 수 내림차순으로 정렬되고, 기타 주제는 항상 마지막에
        온다.
        """
        classified = self.classifier.classify_all(articles)
        groups: Dict[str, List[ClassifiedArticle]] = {}
        for item in classified:
            groups.setdefault(item.topic, []).append(item)

        fallback = self.classifier.fallback_topic
        ordered_topics = sorted(
            groups,
            key=lambda t: (t == fallback, -len(groups[t]), t),
        )
        return OrderedDict((t, groups[t]) for t in ordered_topics)

    def to_markdown(self, groups: "OrderedDict[str, List[ClassifiedArticle]]") -> str:
        """주제별 정리 결과를 Markdown 문서로 만든다."""
        total = sum(len(v) for v in groups.values())
        lines = [
            "# 뉴스 기사 주제별 정리",
            "",
            f"총 **{total}건**의 기사를 **{len(groups)}개** 주제로 정리했습니다.",
            "",
            "## 요약",
            "",
            "| 주제 | 기사 수 |",
            "| --- | ---: |",
        ]
        for topic, items in groups.items():
            lines.append(f"| {topic} | {len(items)} |")
        lines.append("")

        for topic, items in groups.items():
            lines.append(f"## {topic} ({len(items)}건)")
            lines.append("")
            for item in items:
                a = item.article
                meta = " · ".join(x for x in (a.date, a.source) if x)
                lines.append(f"- **{a.title}**" + (f" ({meta})" if meta else ""))
                if a.body:
                    lines.append(f"  - {_snippet(a.body)}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def to_json(self, groups: "OrderedDict[str, List[ClassifiedArticle]]") -> str:
        """주제별 정리 결과를 JSON 문자열로 만든다."""
        payload = {
            "total": sum(len(v) for v in groups.values()),
            "topics": [
                {
                    "topic": topic,
                    "count": len(items),
                    "articles": [item.to_dict() for item in items],
                }
                for topic, items in groups.items()
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
