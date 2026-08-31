# -*- coding: utf-8 -*-
"""연구 노트 검증기.

    python3 research/tools/validate.py

출처 없는 기록, 파일명과 어긋난 티커, 오탈자 난 열거형 값 따위를 잡아낸다.
오류가 하나라도 있으면 종료 코드 1.
"""
from __future__ import annotations

import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import schema  # noqa: E402  pylint: disable=wrong-import-position


class Report:
    """파일별 오류·경고 수집기."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append((schema.rel(path), message))

    def warn(self, path, message):
        self.warnings.append((schema.rel(path), message))


def _require(report, path, meta, fields):
    """필수 필드 존재 여부. 비어 있는 값도 누락으로 본다."""
    missing = [f for f in fields if meta.get(f) in (None, "", [], {})]
    for field in missing:
        report.error(path, f"필수 필드 누락: {field}")
    return not missing


def _enum(report, path, value, allowed, label):
    if value is not None and value not in allowed:
        report.error(
            path, f"{label} 값이 잘못됨: {value!r} (허용: {', '.join(allowed)})"
        )


def _date(report, path, value, label):
    parsed = schema.as_date(value)
    if value is not None and parsed is None:
        report.error(path, f"{label}는 YYYY-MM-DD 형식이어야 함: {value!r}")
    return parsed


def _source_exists(report, path, source, label):
    """영상 노트 참조가 실제 파일을 가리키는지."""
    if not isinstance(source, str):
        report.error(path, f"{label}는 문자열 경로여야 함: {source!r}")
        return False
    target = schema.RESEARCH_ROOT / source
    if not target.is_file():
        report.error(path, f"{label}가 가리키는 파일이 없음: {source}")
        return False
    if not source.startswith("videos/"):
        report.warn(path, f"{label}는 videos/ 아래 영상 노트를 가리키는 편이 좋음: {source}")
    return True


def check_video(report, path, meta):
    if not _require(report, path, meta, ["type", "title", "captured", "source", "confidence"]):
        return
    _enum(report, path, meta.get("source"), schema.SOURCE_KINDS, "source")
    _enum(report, path, meta.get("confidence"), schema.CONFIDENCE, "confidence")
    _enum(report, path, meta.get("access"), schema.ACCESS, "access")

    url = meta.get("url")
    if url is not None and (not isinstance(url, str) or not url.startswith("http")):
        report.error(path, f"url은 http로 시작해야 함: {url!r}")
    if url is None and meta.get("access") != "membership":
        report.warn(path, "url이 없음 (멤버십 전용이면 access: membership 을 명시할 것)")

    published = _date(report, path, meta.get("published"), "published")
    captured = _date(report, path, meta.get("captured"), "captured")
    if published and captured and captured < published:
        report.error(path, f"captured({captured})가 published({published})보다 빠름")
    if published and published > datetime.date.today():
        report.warn(path, f"published가 미래 날짜임: {published}")
    if published is None:
        report.warn(path, "published(공개일)를 모름 — 확인되면 채우고 파일명에 날짜를 붙일 것")

    # 공개일을 아는 노트만 파일명에 날짜를 강제한다. 모르면 자유 슬러그를 허용하되,
    # 날짜처럼 보이는 접두사가 published와 어긋나는 것은 막는다.
    matched = schema.VIDEO_NAME_RE.match(path.stem)
    if published and matched is None:
        report.error(path, "published를 아는 노트의 파일명은 YYYY-MM-DD-<slug>.md 여야 함")
    elif published and matched.group(1) != published.isoformat():
        report.error(
            path, f"파일명 날짜({matched.group(1)})와 published({published})가 다름"
        )
    elif published is None and matched is not None:
        report.error(
            path, f"파일명에 날짜({matched.group(1)})가 있는데 published가 비어 있음"
        )

    episode = meta.get("episode")
    if episode is not None and not isinstance(episode, int):
        report.error(path, f"episode는 정수여야 함: {episode!r}")
    if episode is not None and not meta.get("series"):
        report.error(path, "episode가 있으면 series도 있어야 함")

    tickers = meta.get("tickers")
    if tickers is not None and not isinstance(tickers, list):
        report.error(path, "tickers는 목록이어야 함")


def check_stock(report, path, meta):
    if not _require(report, path, meta, ["type", "ticker", "name", "market", "views"]):
        return
    _enum(report, path, meta.get("market"), schema.MARKETS, "market")

    ticker = meta.get("ticker")
    if str(ticker) != path.stem:
        report.error(path, f"ticker({ticker!r})와 파일명({path.stem})이 다름")

    views = meta.get("views")
    if not isinstance(views, list):
        report.error(path, "views는 목록이어야 함")
        return

    seen = set()
    for index, view in enumerate(views):
        label = f"views[{index}]"
        if not isinstance(view, dict):
            report.error(path, f"{label}는 매핑이어야 함")
            continue
        for field in ("stance", "source"):
            if view.get(field) in (None, ""):
                report.error(path, f"{label}.{field} 누락")
        _enum(report, path, view.get("stance"), schema.STANCES, f"{label}.stance")
        # date는 선택. 강의 공개일을 모르는 자료가 있어 억지 날짜를 넣게 하지 않는다.
        # 대신 색인에서 출처 노트의 날짜로 대체하고, 여기서는 경고만 남긴다.
        view_date = _date(report, path, view.get("date"), f"{label}.date")
        if view.get("date") in (None, ""):
            report.warn(path, f"{label}.date 없음 — 출처 노트의 날짜로 대체됨")
        if view.get("source") is not None:
            _source_exists(report, path, view.get("source"), f"{label}.source")
        for field in ("price", "target_price"):
            value = view.get(field)
            if value is not None and not isinstance(value, (int, float)):
                report.error(path, f"{label}.{field}는 숫자여야 함: {value!r}")
        key = (view_date, view.get("source"))
        if view_date and key in seen:
            report.warn(path, f"{label}: 같은 날짜·출처의 의견이 중복됨")
        seen.add(key)


def check_principle(report, path, meta):
    if not _require(report, path, meta, ["type", "id", "title", "category", "status", "sources"]):
        return
    _enum(report, path, meta.get("category"), schema.CATEGORIES, "category")
    _enum(report, path, meta.get("status"), schema.STATUSES, "status")

    principle_id = meta.get("id")
    if str(principle_id) != path.stem:
        report.error(path, f"id({principle_id!r})와 파일명({path.stem})이 다름")
    elif not schema.PRINCIPLE_ID_RE.match(str(principle_id)):
        report.error(path, f"id는 영소문자·숫자·하이픈만 사용: {principle_id!r}")

    sources = meta.get("sources")
    if not isinstance(sources, list):
        report.error(path, "sources는 목록이어야 함")
        return
    for index, source in enumerate(sources):
        _source_exists(report, path, source, f"sources[{index}]")
    if meta.get("status") == "confirmed" and len(sources) < 2:
        report.warn(
            path, "status가 confirmed인데 출처가 1개뿐임 (tentative가 더 정확할 수 있음)"
        )


CHECKERS = {"video": check_video, "stock": check_stock, "principle": check_principle}


def cross_checks(report, documents):
    """파일 사이의 정합성 검사."""
    known_tickers = {
        str(meta.get("ticker"))
        for _, meta, _ in documents["stock"]
        if isinstance(meta, dict) and meta.get("ticker") is not None
    }
    referenced = set()
    for path, meta, _ in documents["video"]:
        if not isinstance(meta, dict):
            continue
        for ticker in meta.get("tickers") or []:
            referenced.add(str(ticker))
            if str(ticker) not in known_tickers:
                report.warn(
                    path, f"티커 {ticker}에 대응하는 stocks/{ticker}.md 가 아직 없음"
                )

    cited = set()
    for kind in ("stock", "principle"):
        for _, meta, _ in documents[kind]:
            if not isinstance(meta, dict):
                continue
            sources = meta.get("sources") or []
            for view in meta.get("views") or []:
                if isinstance(view, dict) and view.get("source"):
                    cited.add(view["source"])
            for source in sources:
                if isinstance(source, str):
                    cited.add(source)
    for path, meta, _ in documents["video"]:
        if isinstance(meta, dict) and schema.rel(path) not in cited:
            report.warn(path, "이 영상을 인용하는 종목·원칙 노트가 없음 (정리 미완?)")


def main():
    report = Report()
    documents = schema.load_all()

    total = 0
    for kind, entries in documents.items():
        for path, meta, extra in entries:
            total += 1
            if meta is None:
                report.error(path, extra)
                continue
            declared = meta.get("type")
            if declared != kind:
                report.error(
                    path, f"type이 {kind!r}여야 하는데 {declared!r}임 (디렉터리와 불일치)"
                )
                continue
            CHECKERS[kind](report, path, meta)

    cross_checks(report, documents)

    for where, message in report.warnings:
        print(f"경고  {where}: {message}")
    for where, message in report.errors:
        print(f"오류  {where}: {message}")

    print(
        f"\n노트 {total}개 검사 — 오류 {len(report.errors)}개, 경고 {len(report.warnings)}개"
    )
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
