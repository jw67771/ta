# -*- coding: utf-8 -*-
"""연구 노트의 front matter 스키마 정의와 파싱 유틸리티.

노트는 `YAML front matter + Markdown 본문` 형식이다. 필드 정의는 research/SCHEMA.md 참고.
"""
from __future__ import annotations

import datetime
import pathlib
import re

import yaml

RESEARCH_ROOT = pathlib.Path(__file__).resolve().parent.parent

# 문서 종류 -> 디렉터리명
DOC_DIRS = {
    "video": "videos",
    "stock": "stocks",
    "principle": "philosophy",
}

MARKETS = ("KOSPI", "KOSDAQ", "NASDAQ", "NYSE", "AMEX", "TSE", "HKEX", "ETC")
# "사례"는 매매의견이 아니라 강의·설명의 예시로 등장했다는 뜻이다.
# 추천하지 않은 종목에 억지로 스탠스를 붙이지 않기 위해 둔다.
STANCES = ("매수", "비중확대", "관심", "중립", "비중축소", "매도", "보유", "사례")
CONFIDENCE = ("high", "medium", "low")
SOURCE_KINDS = ("transcript", "summary", "manual", "slides")
CATEGORIES = (
    "매수원칙",
    "매도원칙",
    "종목선정",
    "리스크관리",
    "포트폴리오",
    "심리",
    "시장관",
)
STATUSES = ("confirmed", "tentative")
ACCESS = ("public", "membership")

FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)\Z", re.DOTALL)
VIDEO_NAME_RE = re.compile(r"\A(\d{4}-\d{2}-\d{2})-(.+)\Z")
PRINCIPLE_ID_RE = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class FrontMatterError(Exception):
    """front matter를 읽을 수 없을 때."""


def parse(path: pathlib.Path):
    """노트 파일을 (meta, body)로 분해한다."""
    text = path.read_text(encoding="utf-8")
    matched = FRONT_MATTER_RE.match(text)
    if matched is None:
        raise FrontMatterError("YAML front matter(--- ... ---)로 시작하지 않습니다")
    try:
        meta = yaml.safe_load(matched.group(1))
    except yaml.YAMLError as exc:
        raise FrontMatterError(f"front matter YAML 파싱 실패: {exc}") from exc
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise FrontMatterError("front matter는 key: value 매핑이어야 합니다")
    return meta, matched.group(2)


def note_paths(kind: str):
    """해당 종류의 노트 경로를 정렬해 돌려준다. `_`로 시작하는 템플릿은 제외."""
    directory = RESEARCH_ROOT / DOC_DIRS[kind]
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.glob("*.md") if not p.name.startswith("_")
    )


def load(kind: str):
    """(path, meta, body) 목록을 돌려준다. 파싱 실패한 파일은 meta=None."""
    loaded = []
    for path in note_paths(kind):
        try:
            meta, body = parse(path)
        except (FrontMatterError, OSError, UnicodeDecodeError) as exc:
            loaded.append((path, None, str(exc)))
        else:
            loaded.append((path, meta, body))
    return loaded


def load_all():
    """모든 종류를 한 번에 읽는다."""
    return {kind: load(kind) for kind in DOC_DIRS}


def rel(path: pathlib.Path) -> str:
    """research/ 기준 상대경로 문자열."""
    try:
        return path.relative_to(RESEARCH_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def as_date(value):
    """YAML이 date로 파싱했거나 ISO 문자열인 값을 date로. 실패 시 None."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def source_dates():
    """영상 노트 경로 -> 대표 날짜(published 우선, 없으면 captured) 매핑.

    공개일을 모르는 멤버십 강의처럼 date가 비어 있는 의견의 시점을 추정하는 데 쓴다.
    """
    dates = {}
    for path, meta, _ in load("video"):
        if not isinstance(meta, dict):
            continue
        dates[rel(path)] = as_date(meta.get("published")) or as_date(meta.get("captured"))
    return dates


def view_date(view: dict, fallback=None):
    """의견의 시점. date가 없으면 (exact=False로) 출처 노트의 날짜를 쓴다.

    반환값은 (date, exact) 튜플이며, 둘 다 없으면 (None, False).
    """
    explicit = as_date(view.get("date")) if isinstance(view, dict) else None
    if explicit is not None:
        return explicit, True
    if fallback:
        return fallback.get(view.get("source")), False
    return None, False


def latest_view(meta: dict, fallback=None):
    """종목 노트에서 가장 최근 의견 항목을 (view, date, exact)로 돌려준다."""
    views = meta.get("views")
    if not isinstance(views, list):
        return None, None, False
    dated = []
    for view in views:
        if not isinstance(view, dict):
            continue
        when, exact = view_date(view, fallback)
        if when is not None:
            dated.append((view, when, exact))
    if not dated:
        return None, None, False
    return max(dated, key=lambda item: item[1])
