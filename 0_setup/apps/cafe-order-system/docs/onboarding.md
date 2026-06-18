# Cafe Order System — 개발자 온보딩 가이드

## 프로젝트 소개

사내 카페 주문 시스템은 2024년 3분기에 인프라팀에서 개발을 시작했습니다.
직원들의 카페 이용 편의성을 높이고, 바리스타의 주문 관리 효율을 개선하기 위해 만들어졌습니다.

## 로컬 개발 환경 설정

### 사전 요구사항
- Python 3.11+
- pip 또는 poetry

### 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (자동으로 DB 초기화 + 시드 데이터 삽입)
uvicorn app.main:app --reload --port 8000

# API 문서 확인
open http://localhost:8000/docs
```

### 디렉토리 구조

```
cafe-order-system/
├── app/
│   ├── main.py          # FastAPI 앱 초기화, lifespan, 시드 데이터
│   ├── config.py        # 환경 변수, 상수 정의
│   ├── database.py      # SQLAlchemy 엔진/세션 설정
│   ├── models.py        # ORM 모델 (MenuItem, Customer, Order, OrderItem)
│   ├── schemas.py       # Pydantic 요청/응답 스키마
│   ├── routes/
│   │   ├── menu.py      # 메뉴 CRUD
│   │   ├── orders.py    # 주문 생성/상태변경/취소
│   │   └── customers.py # 고객 등록/조회
│   └── services/
│       ├── order_service.py     # 주문 검증, 금액 계산
│       └── inventory_service.py # 인기 메뉴, 카테고리 통계
├── docs/                # 내부 문서
├── tests/               # 테스트 코드
├── Dockerfile
└── requirements.txt
```

## 개발 컨벤션

### 코드 스타일
- PEP 8 준수 (라인 길이 100자)
- Type hints 필수 (함수 파라미터, 리턴 타입)
- Docstring: 복잡한 비즈니스 로직에만 작성

### 브랜치 전략
- `main`: 운영 배포 브랜치
- `develop`: 개발 통합 브랜치
- `feature/xxx`: 기능 개발
- `hotfix/xxx`: 긴급 수정

### 커밋 메시지
```
feat: 새 메뉴 카테고리 추가
fix: 주문 금액 계산 소수점 오류 수정
docs: API 가이드 업데이트
```

## 배포 프로세스

1. `develop` 브랜치에 PR 생성
2. 코드 리뷰 (최소 1명 승인)
3. CI 통과 확인 (lint + test)
4. `main` 머지 → 자동 배포 (OpenShift BuildConfig)

## 자주 묻는 질문

**Q: 새 메뉴 카테고리를 추가하려면?**
A: `app/models.py`의 `MenuCategory` enum에 추가하고, DB 마이그레이션을 실행하세요.

**Q: DB를 초기화하고 싶으면?**
A: `cafe_orders.db` 파일을 삭제하고 서버를 재시작하면 시드 데이터와 함께 새로 생성됩니다.

**Q: 테스트 데이터는 어디서 관리하나요?**
A: `app/main.py`의 `_seed_data()` 함수에서 초기 메뉴와 고객 데이터를 관리합니다.

**Q: OpenShift에서 로그를 확인하려면?**
A: `oc logs deploy/cafe-api -n cafe-system -f`
