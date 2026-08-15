#!/usr/bin/env bash
#
# 새 기록 파일을 만듭니다.
#
#   ./scripts/new-entry.sh <주제> [제목] [날짜]
#
#   ./scripts/new-entry.sh work
#   ./scripts/new-entry.sh health "무릎 재활 3주차"
#   ./scripts/new-entry.sh thoughts "" 2026-08-10
#
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

topics() {
    find "$ROOT/topics" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
}

topic=${1:-}
title=${2:-}
date=${3:-$(date +%Y-%m-%d)}

if [ -z "$topic" ]; then
    echo "사용법: $(basename "$0") <주제> [제목] [날짜]" >&2
    echo >&2
    echo "쓸 수 있는 주제:" >&2
    topics | sed 's/^/  /' >&2
    exit 1
fi

if [ ! -d "$ROOT/topics/$topic" ]; then
    echo "'$topic' 주제가 없습니다." >&2
    echo >&2
    echo "쓸 수 있는 주제:" >&2
    topics | sed 's/^/  /' >&2
    echo >&2
    echo "새로 만들려면: mkdir -p topics/$topic" >&2
    exit 1
fi

if ! printf '%s' "$date" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
    echo "날짜는 YYYY-MM-DD 형식이어야 합니다: $date" >&2
    exit 1
fi

year=${date%%-*}
dir="$ROOT/topics/$topic/$year"
file="$dir/$date.md"

if [ -e "$file" ]; then
    echo "이미 있습니다: ${file#"$ROOT"/}"
    exit 0
fi

[ -n "$title" ] || title=$date

template=$(cat "$ROOT/templates/entry.md")
content=${template//\{\{DATE\}\}/$date}
content=${content//\{\{TOPIC\}\}/$topic}
content=${content//\{\{TITLE\}\}/$title}

mkdir -p "$dir"
printf '%s' "$content" > "$file"

echo "만들었습니다: ${file#"$ROOT"/}"
