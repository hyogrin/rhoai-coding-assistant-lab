# Cafe Order System — Architecture

## Overview

사내 카페 주문 관리 시스템으로, 직원들이 사번으로 인증하여 음료/베이커리를 주문하고
바리스타가 주문 상태를 관리할 수 있는 REST API 기반 백엔드 서비스입니다.

## System Components

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Mobile/Web App │────▶│  FastAPI Server  │────▶│   SQLite    │
│  (클라이언트)    │     │  (cafe-api pod)  │     │  (PV 마운트) │
└─────────────────┘     └──────────────────┘     └─────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         └─────────────▶│  Health Check    │
                        │  (/health)       │
                        └──────────────────┘
```

## Layer Architecture

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Router | `app/routes/` | HTTP 요청 처리, 입력 검증, 응답 포맷팅 |
| Service | `app/services/` | 비즈니스 로직 (주문 금액 계산, 재고 확인) |
| Model | `app/models.py` | SQLAlchemy ORM 모델, DB 스키마 정의 |
| Schema | `app/schemas.py` | Pydantic 요청/응답 DTO |
| Database | `app/database.py` | 연결 관리, 세션 팩토리 |

## Data Model (ERD)

```
MenuItem (1) ──── (N) OrderItem (N) ──── (1) Order (N) ──── (1) Customer
  - id                 - id                 - id                - id
  - name               - quantity           - status            - employee_id
  - category           - customization      - total_amount      - name
  - price              - menu_item_id       - customer_id       - department
  - is_available       - order_id           - notes             - email
  - calories                                - created_at
  - allergens                               - pickup_time
```

## Order Status Flow

```
PENDING → CONFIRMED → PREPARING → READY → PICKED_UP
   │          │
   └──────────┴───────→ CANCELLED
```

- **PENDING**: 주문 접수됨 (자동)
- **CONFIRMED**: 바리스타가 주문 확인
- **PREPARING**: 음료/음식 제조 중
- **READY**: 픽업 대기
- **PICKED_UP**: 고객이 수령 완료
- **CANCELLED**: 주문 취소 (PENDING 또는 CONFIRMED 상태에서만 가능)

## Deployment

OpenShift에 단일 Pod로 배포됩니다:
- **Namespace**: `cafe-system`
- **Deployment**: `cafe-api`
- **Service Port**: 8000
- **Route**: `cafe-api-cafe-system.apps.<cluster>`
- **Storage**: PVC를 통한 SQLite 파일 영속화 (향후 PostgreSQL 전환 계획)

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ |
| Validation | Pydantic | 2.0+ |
| Database | SQLite | 3.x |
| Runtime | Python | 3.11 |
| Container | UBI 9 minimal | latest |

## Non-Functional Requirements

- **응답시간**: p99 < 200ms
- **가용성**: 업무시간(08:00-18:00) 99.5%
- **동시사용자**: 최대 100명
- **데이터 보존**: 주문 데이터 6개월 보관 후 아카이브
