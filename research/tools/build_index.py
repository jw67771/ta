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


def _cell(text):
    """표 칸에 넣을 문자열. 파이프는 표를 깨뜨리므로 이스케이프한다."""
    return str(text).replace("|", "\\|")


def _label(text):
    """링크 표시 문자열. 대괄호는 링크 문법을 깨뜨리므로 함께 이스케이프한다."""
    return _cell(text).replace("[", "\\[").replace("]", "\\]")


def _title(meta, path):
    """색인에 쓸 제목. 시리즈 열과 겹치는 '[시리즈]' 접두사는 덜어낸다."""
    title = str(meta.get("title", path.stem))
    series = meta.get("series")
    if series:
        prefix = f"[{series}]"
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    return title


def _link(path):
    rel = schema.rel(path)
    return f"[{_label(path.stem)}]({rel})"


def _num(value):
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return "-"


def _valid(entries):
    return [(p, m, b) for p, m, b in entries if isinstance(m, dict)]


def stock_section(entries, fallback):
    lines = ["## 종목", ""]
    if not entries:
        lines += ["_아직 없음._", ""]
        return lines

    rows = []
    approximate = False
    for path, meta, _ in entries:
        view, when, exact = schema.latest_view(meta, fallback)
        if when and not exact:
            approximate = True
        rows.append(
            {
                "sort": when or schema.as_date("1900-01-01"),
                "cells": [
                    _link(path),
                    _cell(meta.get("name", "-")),
                    _cell(meta.get("market", "-")),
                    _cell(meta.get("sector") or "-"),
                    (when.isoformat() + ("" if exact else "~")) if when else "-",
                    _cell(view.get("stance", "-")) if view else "-",
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
    if approximate:
        lines += [
            "`~` 표시는 의견 날짜를 몰라 출처 노트의 날짜로 대신한 것입니다.",
            "`사례` 스탠스는 매매의견이 아니라 강의 예시로 등장했다는 뜻입니다.",
            "",
        ]
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
                f"- [{_label(meta.get('title', path.stem))}]({schema.rel(path)})"
                f"{mark} — 출처 {count}건"
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
        captured = schema.as_date(meta.get("captured"))
        tickers = _cell(", ".join(str(x) for x in (meta.get("tickers") or [])) or "-")
        series = meta.get("series")
        episode = meta.get("episode")
        label = _cell(f"{series} {episode}화" if series and episode else (series or "-"))
        rows.append(
            {
                "sort": published or captured or schema.as_date("1900-01-01"),
                "sub": episode if isinstance(episode, int) else 0,
                "cells": [
                    published.isoformat() if published else "미상",
                    label,
                    f"[{_label(_title(meta, path))}]({schema.rel(path)})",
                    tickers,
                    _cell(f"{meta.get('source', '-')}/{meta.get('confidence', '-')}"),
                ],
            }
        )
    rows.sort(key=lambda r: (r["sort"], r["sub"]), reverse=True)

    lines += ["| 공개일 | 시리즈 | 제목 | 종목 | 출처/신뢰도 |", "|---|---|---|---|---|"]
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
    lines += stock_section(stocks, schema.source_dates())
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
