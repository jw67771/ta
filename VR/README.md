# VR

신규 프로젝트 'VR' 입니다.

## 프로젝트 구조

```
VR/
├── README.md          # 프로젝트 소개 문서
├── pyproject.toml     # 패키지 및 빌드 설정
├── requirements.txt   # 의존성 목록
├── vr/                # 메인 패키지
│   ├── __init__.py
│   └── main.py
└── tests/             # 테스트 코드
    └── test_main.py
```

## 시작하기

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
python -m vr.main

# 테스트
python -m pytest tests/
```
