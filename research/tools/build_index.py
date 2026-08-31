# -*- coding: utf-8 -*-
"""research/INDEX.md 생성기.

    python3 research/tools/build_index.py          # INDEX.md 갱신
    python3 research/tools/build_index.py --check  # 갱신 필요 여부만 확인 (CI용)

노트가 늘어나면 손으로 만든 목차는 반드시 낡는다. 색인은 항상 파일에서 다시 만든다.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import schema  # noqa: E402  pylint: disable=wrong-import-position

INDEX_PATH = schema.RESEARCH_ROOT / "INDEX.md"
HEADER = "<!-- 이 파일은 research/tools/build_index.py 가 생성합니다. 직접 고치지 마세요. -->"


def _link(path):
    rel = schema.rel(path)
    return f"[{path.stem}]({rel})"


def _num(value):
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return "-"


def _valid(entries):
    return [(p, m, b) for p, m, b in entries if isinstance(m, dict)]


def stock_section(entries):
    lines = ["## 종목", ""]
    if not entries:
        lines += ["_아직 없음._", ""]
        return lines

    rows = []
    for path, meta, _ in entries:
        view = schema.latest_view(meta)
        view_date = schema.as_date(view.get("date")) if view else None
        rows.append(
            {
                "sort": view_date or schema.as_date("1900-01-01"),
                "cells": [
                    _link(path),
                    str(meta.get("name", "-")),
                    str(meta.get("market", "-")),
                    str(meta.get("sector") or "-"),
                    view_date.isoformat() if view_date else "-",
                    str(view.get("stance", "-")) if view else "-",
                    _num(view.get("target_price")) if view else "-",
                    str(len(meta.get("views") or [])),
                ],
            }
        )
    rows.sort(key=lambda r: r["sort"], reverse=True)

    lines += [
        "| 티커 | 종목명 | 시장 | 섹터 | 최신 의견일 | 스탠스 | 목표가 | 의견 수 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += ["| " + " | ".join(r["cells"]) + " |" for r in rows]
    lines.append("")
    return lines


def principle_section(entries):
    lines = ["## 투자 원칙", ""]
    if not entries:
        lines += ["_아직 없음._", ""]
        return lines

    grouped = collections.defaultdict(list)
    for path, meta, _ in entries:
        grouped[str(meta.get("category", "미분류"))].append((path, meta))

    order = [c for c in schema.CATEGORIES if c in grouped]
    order += sorted(c for c in grouped if c not in schema.CATEGORIES)

    for category in order:
        lines += [f"### {category}", ""]
        for path, meta in sorted(grouped[category], key=lambda x: str(x[1].get("title", ""))):
            status = meta.get("status")
            mark = "" if status == "confirmed" else " _(잠정)_"
            count = len(meta.get("sources") or [])
            lines.append(
                f"- [{meta.get('title', path.stem)}]({schema.rel(path)}){mark} — 출처 {count}건"
            )
        lines.append("")
    return lines


def video_section(entries):
    lines = ["## 영상 노트", ""]
    if not entries:
        lines += ["_아직 없음._", ""]
        return lines

    rows = []
    for path, meta, _ in entries:
        published = schema.as_date(meta.get("published"))
        tickers = ", ".join(str(t) for t in (meta.get("tickers") or [])) or "-"
        rows.append(
            {
                "sort": published or schema.as_date("1900-01-01"),
                "cells": [
                    published.isoformat() if published else "-",
                    f"[{meta.get('title', path.stem)}]({schema.rel(path)})",
                    tickers,
                    f"{meta.get('source', '-')}/{meta.get('confidence', '-')}",
                ],
            }
        )
    rows.sort(key=lambda r: r["sort"], reverse=True)

    lines += ["| 공개일 | 제목 | 종목 | 출처/신뢰도 |", "|---|---|---|---|"]
    lines += ["| " + " | ".join(r["cells"]) + " |" for r in rows]
    lines.append("")
    return lines


def render():
    documents = schema.load_all()
    stocks = _valid(documents["stock"])
    principles = _valid(documents["principle"])
    videos = _valid(documents["video"])

    lines = [
        HEADER,
        "",
        "# 색인",
        "",
        f"종목 {len(stocks)} · 원칙 {len(principles)} · 영상 노트 {len(videos)}",
        "",
    ]
    lines += stock_section(stocks)
    lines += principle_section(principles)
    lines += video_section(videos)
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="research/INDEX.md 생성")
    parser.add_argument(
        "--check", action="store_true", help="파일을 쓰지 않고 갱신 필요 여부만 확인"
    )
    args = parser.parse_args()

    content = render()
    current = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.is_file() else None

    if args.check:
        if current == content:
            print("INDEX.md 최신 상태")
            return 0
        print("INDEX.md 가 오래됨 — python3 research/tools/build_index.py 실행 필요")
        return 1

    if current == content:
        print("INDEX.md 변경 없음")
        return 0
    INDEX_PATH.write_text(content, encoding="utf-8")
    print(f"INDEX.md 갱신 -> {schema.rel(INDEX_PATH)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
