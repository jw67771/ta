"""News Topic Organizer - 뉴스 기사를 주제별로 자동 분류·정리하는 도구."""

from .classifier import TopicClassifier, DEFAULT_TOPICS
from .models import Article, ClassifiedArticle
from .organizer import NewsOrganizer

__version__ = "0.1.0"

__all__ = [
    "Article",
    "ClassifiedArticle",
    "TopicClassifier",
    "NewsOrganizer",
    "DEFAULT_TOPICS",
]
