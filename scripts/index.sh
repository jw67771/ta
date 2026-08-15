#!/usr/bin/env bash
#
# 최근 기록을 최신순으로 보여줍니다.
#
#   ./scripts/index.sh [주제] [개수]
#
#   ./scripts/index.sh              # 전체에서 최근 20개
#   ./scripts/index.sh work         # work 주제만
#   ./scripts/index.sh "" 50        # 전체에서 최근 50개
#
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

topic=${1:-}
limit=${2:-20}

if ! printf '%s' "$limit" | grep -Eq '^[0-9]+$'; then
    echo "개수는 숫자여야 합니다: $limit" >&2
    exit 1
fi

if [ -n "$topic" ]; then
    if [ ! -d "$ROOT/topics/$topic" ]; then
        echo "'$topic' 주제가 없습니다." >&2
        exit 1
    fi
    search="$ROOT/topics/$topic"
else
    search="$ROOT/topics"
fi

# 파일명(= 날짜)을 앞에 붙여서 정렬한 뒤 최신순으로 자릅니다.
rows=$(
    find "$search" -type f -name '*.md' ! -name 'README.md' -print \
        | while IFS= read -r f; do
            printf '%s\t%s\n' "$(basename "$f" .md)" "$f"
        done \
        | sort -r \
        | head -n "$limit"
)

if [ -z "$rows" ]; then
    echo "아직 기록이 없습니다."
    exit 0
fi

while IFS=$'\t' read -r date file; do
    rel=${file#"$ROOT"/topics/}
    entry_topic=${rel%%/*}
    title=$(grep -m1 '^# ' "$file" 2>/dev/null | sed 's/^# //') || true
    [ -n "$title" ] || title="(제목 없음)"
    printf '%s  %-10s %s\n' "$date" "$entry_topic" "$title"
done <<< "$rows"
