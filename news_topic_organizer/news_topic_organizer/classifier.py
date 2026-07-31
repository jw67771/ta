"""키워드 기반 주제 분류기.

외부 의존성 없이 동작하는 규칙 기반 분류기입니다. 주제별 키워드 사전을
바탕으로 기사 텍스트와의 매칭 점수를 계산해 가장 점수가 높은 주제를
배정합니다. 제목에 등장한 키워드는 본문보다 높은 가중치를 받습니다.

사용자 정의 주제 사전(JSON)을 넘겨 기본 사전을 대체하거나 확장할 수
있습니다.
"""

import re
from typing import Dict, Iterable, List, Optional, Tuple

from .models import Article, ClassifiedArticle

# 매칭 실패 시 배정되는 주제 이름
FALLBACK_TOPIC = "기타"

# 제목에서 매칭된 키워드에 곱해지는 가중치
TITLE_WEIGHT = 3.0

# 주제 배정에 필요한 최소 점수 (미만이면 FALLBACK_TOPIC)
MIN_SCORE = 1.0

DEFAULT_TOPICS: Dict[str, List[str]] = {
    "정치": [
        "대통령", "국회", "여당", "야당", "총선", "대선", "정당", "의원",
        "법안", "개헌", "청와대", "국정감사", "탄핵", "내각", "장관",
        "선거", "공천", "정치권", "여야",
        "president", "parliament", "congress", "senate", "election",
        "policy", "minister", "lawmaker", "legislation",
    ],
    "경제": [
        "금리", "주가", "증시", "코스피", "코스닥", "환율", "물가",
        "인플레이션", "수출", "무역", "부동산", "경기", "투자", "기업",
        "실적", "고용", "일자리", "한국은행", "재정", "세금", "가계부채",
        "경제성장", "GDP", "주식", "채권",
        "economy", "stock", "market", "inflation", "interest rate",
        "trade", "investment", "earnings", "recession", "unemployment",
    ],
    "사회": [
        "경찰", "검찰", "법원", "재판", "판결", "사건", "사고", "화재",
        "범죄", "교육", "학교", "대학", "입시", "노동", "노조", "파업",
        "복지", "인구", "저출산", "고령화", "주거", "안전", "재난",
        "crime", "court", "police", "trial", "education", "welfare",
        "accident", "strike", "labor",
    ],
    "IT/과학": [
        "인공지능", "AI", "반도체", "소프트웨어", "스타트업", "플랫폼",
        "데이터", "클라우드", "로봇", "우주", "위성", "발사", "연구",
        "과학", "기술", "스마트폰", "배터리", "전기차", "자율주행",
        "블록체인", "암호화폐", "메타버스", "양자",
        "artificial intelligence", "semiconductor", "software", "startup",
        "technology", "research", "robot", "space", "quantum", "chip",
        "machine learning", "cybersecurity",
    ],
    "스포츠": [
        "야구", "축구", "농구", "배구", "골프", "올림픽", "월드컵",
        "리그", "구단", "감독", "선수", "경기", "우승", "결승", "홈런",
        "골", "메달", "프로야구", "K리그", "손흥민",
        "baseball", "football", "soccer", "basketball", "olympic",
        "world cup", "championship", "tournament", "athlete", "league",
    ],
    "문화": [
        "영화", "드라마", "음악", "공연", "전시", "미술", "문학", "소설",
        "출판", "K팝", "아이돌", "배우", "감독상", "영화제", "박물관",
        "문화재", "축제", "예술", "콘서트", "앨범",
        "movie", "film", "drama", "music", "concert", "exhibition",
        "art", "novel", "festival", "album", "k-pop",
    ],
    "국제": [
        "미국", "중국", "일본", "러시아", "유럽", "북한", "유엔", "정상회담",
        "외교", "국제", "전쟁", "분쟁", "제재", "협정", "나토", "백악관",
        "국경", "난민", "핵협상",
        "united states", "china", "japan", "russia", "europe", "diplomacy",
        "summit", "sanction", "war", "conflict", "nato", "united nations",
    ],
    "건강": [
        "건강", "질병", "암", "치료", "백신", "감염", "바이러스", "의료",
        "병원", "의사", "환자", "수술", "약물", "신약", "임상", "정신건강",
        "운동", "식단", "비만", "당뇨",
        "health", "disease", "cancer", "vaccine", "virus", "hospital",
        "patient", "treatment", "clinical", "diabetes", "mental health",
    ],
}


def _tokenize(text: str) -> str:
    """매칭용으로 텍스트를 정규화(소문자화·공백 정리)한다."""
    return re.sub(r"\s+", " ", text.lower()).strip()


class TopicClassifier:
    """주제별 키워드 사전으로 기사를 분류하는 분류기."""

    def __init__(
        self,
        topics: Optional[Dict[str, List[str]]] = None,
        fallback_topic: str = FALLBACK_TOPIC,
        min_score: float = MIN_SCORE,
        title_weight: float = TITLE_WEIGHT,
    ):
        self.topics = topics if topics else DEFAULT_TOPICS
        self.fallback_topic = fallback_topic
        self.min_score = min_score
        self.title_weight = title_weight
        # 키워드를 미리 정규화해 둔다
        self._normalized: Dict[str, List[str]] = {
            topic: [_tokenize(kw) for kw in keywords]
            for topic, keywords in self.topics.items()
        }

    def _count_matches(self, text: str, keywords: List[str]) -> float:
        score = 0.0
        for kw in keywords:
            if not kw:
                continue
            # 영문/숫자로만 된 키워드는 단어 경계를 지켜 매칭하고,
            # 한글 등은 부분 문자열 매칭(조사가 붙는 교착어 특성 대응)
            if re.fullmatch(r"[a-z0-9 .\-]+", kw):
                pattern = r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])"
                score += len(re.findall(pattern, text))
            else:
                score += text.count(kw)
        return score

    def score(self, article: Article) -> Dict[str, float]:
        """기사에 대한 주제별 점수를 계산한다."""
        title = _tokenize(article.title)
        body = _tokenize(article.body)
        scores: Dict[str, float] = {}
        for topic, keywords in self._normalized.items():
            title_hits = self._count_matches(title, keywords)
            body_hits = self._count_matches(body, keywords)
            scores[topic] = title_hits * self.title_weight + body_hits
        return scores

    def classify(self, article: Article) -> ClassifiedArticle:
        """기사 한 건을 분류한다."""
        scores = self.score(article)
        best_topic, best_score = max(
            scores.items(), key=lambda item: item[1], default=(self.fallback_topic, 0.0)
        )
        if best_score < self.min_score:
            best_topic = self.fallback_topic
        return ClassifiedArticle(article=article, topic=best_topic, scores=scores)

    def classify_all(self, articles: Iterable[Article]) -> List[ClassifiedArticle]:
        """여러 기사를 한 번에 분류한다."""
        return [self.classify(a) for a in articles]
