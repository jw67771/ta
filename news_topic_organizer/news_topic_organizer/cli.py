"""커맨드라인 인터페이스.

사용 예::

    # 디렉터리의 기사들을 주제별로 정리해 Markdown으로 출력
    python -m news_topic_organizer examples/articles

    # JSON으로 출력하고 파일로 저장
    python -m news_topic_organizer articles/ --format json -o result.json

    # 표준입력으로 기사 전달 ('---' 구분선으로 여러 건)
    cat articles.txt | python -m news_topic_organizer -

    # 사용자 정의 주제 사전 사용
    python -m news_topic_organizer articles/ --topics my_topics.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from .classifier import TopicClassifier
from .loader import load_path, load_text
from .models import Article
from .organizer import NewsOrganizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="news-topic-organizer",
        description="뉴스 기사를 주제별로 자동 분류·정리합니다.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="기사 파일(.txt/.json)이나 디렉터리 경로. '-'는 표준입력.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("markdown", "json"),
        default="markdown",
        help="출력 형식 (기본: markdown)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="결과를 저장할 파일 경로. 생략하면 표준출력.",
    )
    parser.add_argument(
        "--topics",
        help="사용자 정의 주제 사전 JSON 파일 ({\"주제\": [\"키워드\", ...]}).",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    articles: List[Article] = []
    for source in args.inputs:
        if source == "-":
            articles.extend(load_text(sys.stdin.read(), source="<stdin>"))
        else:
            path = Path(source)
            if not path.exists():
                print(f"오류: 경로를 찾을 수 없습니다: {source}", file=sys.stderr)
                return 1
            articles.extend(load_path(path))

    if not articles:
        print("오류: 입력에서 기사를 찾지 못했습니다.", file=sys.stderr)
        return 1

    topics = None
    if args.topics:
        topics = json.loads(Path(args.topics).read_text(encoding="utf-8"))

    organizer = NewsOrganizer(TopicClassifier(topics=topics))
    groups = organizer.organize(articles)

    if args.format == "json":
        result = organizer.to_json(groups)
    else:
        result = organizer.to_markdown(groups)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"결과를 저장했습니다: {args.output}", file=sys.stderr)
    else:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
