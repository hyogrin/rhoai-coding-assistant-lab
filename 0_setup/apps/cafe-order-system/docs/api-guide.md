# Cafe Order System — API Guide

## Base URL

```
https://cafe-api-cafe-system.apps.<cluster-domain>
```

## Authentication

현재 사내망 한정 서비스로 별도 인증 없이 운영됩니다.
향후 OpenShift OAuth Proxy를 통한 SSO 연동 예정입니다.

---

## Endpoints

### Health Check

```
GET /health
```

Response:
```json
{"status": "healthy", "service": "Cafe Order System", "version": "1.2.0"}
```

---

### Menu

#### 메뉴 목록 조회
```
GET /api/menu/?category={category}&available_only={bool}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| category | string | null | coffee, tea, smoothie, bakery, sandwich |
| available_only | bool | true | 판매 가능한 메뉴만 조회 |

#### 메뉴 검색
```
GET /api/menu/search/?q={keyword}
```

#### 메뉴 등록
```
POST /api/menu/
Content-Type: application/json

{
  "name": "새 메뉴",
  "category": "coffee",
  "price": 5500,
  "description": "설명",
  "calories": 150,
  "allergens": "우유"
}
```

#### 메뉴 품절 토글
```
PATCH /api/menu/{item_id}/availability
```

---

### Orders

#### 주문 목록
```
GET /api/orders/?status={status}&customer_id={id}&limit={n}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| status | string | null | pending, confirmed, preparing, ready, picked_up, cancelled |
| customer_id | int | null | 특정 고객의 주문만 조회 |
| limit | int | 50 | 최대 반환 건수 |

#### 주문 생성
```
POST /api/orders/
Content-Type: application/json

{
  "customer_id": 1,
  "items": [
    {"menu_item_id": 1, "quantity": 2, "customization": "샷 추가"},
    {"menu_item_id": 11, "quantity": 1}
  ],
  "notes": "11시 픽업 희망"
}
```

**제약사항:**
- 한 주문당 최대 20개 아이템
- 품절 메뉴 주문 불가
- customer_id는 등록된 고객만 가능

#### 주문 상태 변경
```
PATCH /api/orders/{order_id}/status
Content-Type: application/json

{"status": "confirmed"}
```

**상태 전이 규칙:**
- pending → confirmed, cancelled
- confirmed → preparing, cancelled
- preparing → ready
- ready → picked_up

#### 주문 취소
```
DELETE /api/orders/{order_id}
```
pending 또는 confirmed 상태에서만 가능합니다.

---

### Customers

#### 고객 목록
```
GET /api/customers/?department={dept}
```

#### 고객 조회 (사번)
```
GET /api/customers/{employee_id}
```

#### 고객 등록
```
POST /api/customers/
Content-Type: application/json

{
  "employee_id": "EMP006",
  "name": "홍길동",
  "department": "개발팀",
  "email": "gildong.hong@corp.internal",
  "phone": "010-1234-5678"
}
```

#### 고객 주문 이력
```
GET /api/customers/{employee_id}/orders
```

---

### Statistics

```
GET /api/stats
```

Response:
```json
{
  "popular_items": [
    {"name": "아메리카노", "category": "coffee", "total_ordered": 42}
  ],
  "category_summary": [
    {"category": "coffee", "available_count": 5}
  ]
}
```

---

## Error Responses

모든 에러는 다음 형식으로 반환됩니다:

```json
{"detail": "에러 메시지"}
```

| Status Code | Description |
|-------------|-------------|
| 400 | 잘못된 요청 (입력 검증 실패, 상태 전이 불가 등) |
| 404 | 리소스를 찾을 수 없음 |
| 409 | 충돌 (이미 등록된 사번 등) |
| 422 | 요청 본문 형식 오류 |
