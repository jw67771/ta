"""기사 입력 로더.

지원 형식:
  - ``.txt``  : 첫 줄이 제목, 나머지가 본문. ``---`` 구분선으로 한 파일에
                여러 기사를 담을 수 있음.
  - ``.json`` : 기사 객체 하나 또는 기사 객체 배열.
                필드: title(필수), body/content, source, date
  - 디렉터리  : 내부의 .txt/.json 파일을 재귀적으로 모두 읽음.
"""

import json
from pathlib import Path
from typing import List, Union

from .models import Article

ARTICLE_SEPARATOR = "---"


def _from_json_obj(obj: dict, source: str) -> Article:
    return Article(
        title=str(obj.get("title", "")).strip(),
        body=str(obj.get("body", obj.get("content", ""))).strip(),
        source=obj.get("source", source),
        date=obj.get("date"),
    )


def load_text(text: str, source: str = "<text>") -> List[Article]:
    """평문 텍스트에서 기사 목록을 파싱한다."""
    articles = []
    for chunk in text.split(f"\n{ARTICLE_SEPARATOR}\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if title:
            articles.append(Article(title=title, body=body, source=source))
    return articles


def load_file(path: Union[str, Path]) -> List[Article]:
    """단일 파일(.txt 또는 .json)에서 기사를 읽는다."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return [_from_json_obj(obj, str(path)) for obj in data if obj.get("title")]
    return load_text(raw, source=str(path))


def load_path(path: Union[str, Path]) -> List[Article]:
    """파일 또는 디렉터리에서 기사를 읽는다."""
    path = Path(path)
    if path.is_dir():
        articles: List[Article] = []
        for file in sorted(path.rglob("*")):
            if file.suffix.lower() in (".txt", ".json") and file.is_file():
                articles.extend(load_file(file))
        return articles
    return load_file(path)
