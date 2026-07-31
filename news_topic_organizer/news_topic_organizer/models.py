"""데이터 모델 정의."""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Article:
    """뉴스 기사 한 건.

    Attributes:
        title: 기사 제목.
        body: 기사 본문.
        source: 출처 (파일 경로, 언론사 이름 등). 선택.
        date: 발행일 문자열. 선택.
    """

    title: str
    body: str = ""
    source: Optional[str] = None
    date: Optional[str] = None

    @property
    def text(self) -> str:
        """제목과 본문을 합친 전체 텍스트."""
        return f"{self.title}\n{self.body}".strip()


@dataclass
class ClassifiedArticle:
    """분류 결과가 붙은 기사.

    Attributes:
        article: 원본 기사.
        topic: 배정된 주제 이름 (매칭 실패 시 '기타').
        scores: 주제별 매칭 점수.
    """

    article: Article
    topic: str
    scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.article.title,
            "source": self.article.source,
            "date": self.article.date,
            "topic": self.topic,
            "scores": {k: round(v, 4) for k, v in self.scores.items() if v > 0},
        }
