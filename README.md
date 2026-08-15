# 일상 기록

주제별로 나눠서 남기는 개인 기록 저장소입니다.

## 구조

```
topics/
  work/      업무, 프로젝트, 커리어
  health/    건강, 운동, 컨디션, 수면
  reading/   독서, 강의, 배운 것
  thoughts/  생각, 회고, 고민
  life/      일상, 사람, 사건, 여행

templates/entry.md    새 기록의 기본 틀
scripts/              기록 생성 / 목록 조회 도구
```

각 기록은 주제 폴더 아래 연도별로 쌓입니다.

```
topics/work/2026/2026-08-15.md
topics/health/2026/2026-08-15.md
```

같은 날 여러 주제에 쓸 수 있고, 안 쓴 주제는 그냥 비워두면 됩니다. 매일 다 채울
필요는 없습니다.

## 사용법

새 기록 만들기 — 주제 이름만 넘기면 오늘 날짜로 파일이 생깁니다.

```bash
./scripts/new-entry.sh work
./scripts/new-entry.sh health "무릎 재활 3주차"
```

이미 그 날짜 파일이 있으면 덮어쓰지 않고 경로만 알려줍니다. 특정 날짜로 만들려면
세 번째 인자에 날짜를 주세요.

```bash
./scripts/new-entry.sh thoughts "" 2026-08-10
```

최근 기록 훑어보기:

```bash
./scripts/index.sh              # 전체에서 최근 20개
./scripts/index.sh work         # work 주제만
./scripts/index.sh "" 50        # 전체에서 최근 50개
```

## 기록 형식

파일 맨 위에 front-matter가 들어갑니다. 나중에 태그나 날짜로 뽑아 쓰기 위한
것이고, 귀찮으면 `tags`는 비워둬도 됩니다.

```markdown
---
date: 2026-08-15
topic: work
tags: []
---

# 제목

본문
```

## 주제 추가하기

`topics/` 아래에 폴더를 만들면 그게 곧 새 주제입니다. 스크립트는 폴더 목록을 그때
그때 읽으므로 따로 등록할 곳은 없습니다.

```bash
mkdir -p topics/cooking
```

## 비공개 저장소로 옮기기

이 저장소(`jw67771/ta`)는 공개 상태이고, GitHub은 공개 저장소의 포크를 비공개로
전환할 수 없습니다. 실제 기록을 쓰기 전에 비공개 저장소로 옮기는 것을 권합니다.

1. GitHub에서 새 저장소를 **Private**으로 만듭니다 (예: `daily-log`). README 등
   초기화 옵션은 모두 끕니다.
2. 이 브랜치의 내용만 새 저장소로 밀어 넣습니다.

```bash
git remote add private https://github.com/jw67771/daily-log.git
git push private HEAD:main
```

3. 이후로는 새 저장소를 클론해서 씁니다.

```bash
git clone https://github.com/jw67771/daily-log.git
```

옮기고 나면 이 브랜치는 지워도 됩니다. `ta` 저장소의 `master`에는 원래의
Technical Analysis 라이브러리가 그대로 남아 있습니다.
