# Cafe Order System — 운영 런북

## 서비스 정보

| 항목 | 값 |
|------|-----|
| 서비스명 | cafe-order-system |
| 네임스페이스 | cafe-system |
| 팀 | 인프라팀 |
| 당직 | 박준호 (EMP003), 김민수 (EMP001) |
| SLA | 99.5% (업무시간) |

## 일상 운영

### 서비스 상태 확인

```bash
# Pod 상태
oc get pods -n cafe-system

# 헬스체크
curl https://cafe-api-cafe-system.apps.<cluster>/health

# 최근 로그
oc logs deploy/cafe-api -n cafe-system --tail=100
```

### DB 백업

SQLite 파일 백업 (매일 02:00 CronJob):
```bash
oc get cronjob -n cafe-system
# cafe-db-backup  02:00  ...
```

수동 백업:
```bash
oc exec deploy/cafe-api -n cafe-system -- cp /data/cafe_orders.db /data/backup/cafe_orders_$(date +%Y%m%d).db
```

---

## 장애 대응

### Case 1: Pod CrashLoopBackOff

**증상**: Pod가 반복적으로 재시작됨

**진단**:
```bash
oc describe pod -l app=cafe-api -n cafe-system
oc logs deploy/cafe-api -n cafe-system --previous
```

**일반적 원인**:
1. DB 파일 권한 문제 → PVC 마운트 확인
2. 메모리 초과 → 리소스 제한 상향 검토
3. 의존성 에러 → 이미지 재빌드

**조치**:
```bash
# Pod 재시작
oc rollout restart deploy/cafe-api -n cafe-system

# PVC 권한 확인
oc exec deploy/cafe-api -n cafe-system -- ls -la /data/
```

### Case 2: 응답 지연 (p99 > 500ms)

**진단**:
```bash
# Pod 리소스 사용량
oc adm top pod -n cafe-system

# DB 크기 확인
oc exec deploy/cafe-api -n cafe-system -- ls -lh /data/cafe_orders.db
```

**조치**:
1. 오래된 주문 데이터 아카이브 (6개월 이상)
2. Pod replica 증가 (SQLite → PostgreSQL 전환 필요)
3. 임시: Pod 재시작으로 DB 커넥션 풀 초기화

### Case 3: DB 손상

**증상**: `sqlite3.DatabaseError: database disk image is malformed`

**조치**:
```bash
# 최근 백업에서 복원
oc exec deploy/cafe-api -n cafe-system -- \
  cp /data/backup/cafe_orders_latest.db /data/cafe_orders.db

# Pod 재시작
oc rollout restart deploy/cafe-api -n cafe-system
```

> ⚠️ 백업 이후의 주문 데이터는 유실됩니다. 복원 후 바리스타에게 안내 필요.

### Case 4: 메뉴가 전부 품절로 표시됨

**원인**: 관리자가 실수로 일괄 품절 처리했거나 DB 이상

**조치**:
```bash
# 현재 메뉴 상태 확인
curl https://cafe-api-cafe-system.apps.<cluster>/api/menu/?available_only=false

# 개별 메뉴 품절 해제
curl -X PATCH https://cafe-api-cafe-system.apps.<cluster>/api/menu/{item_id}/availability
```

---

## 스케일링

### 현재 구성
- Replica: 1
- CPU request/limit: 100m / 500m
- Memory request/limit: 128Mi / 256Mi

### 스케일 업 기준
- 동시 사용자 100명 초과 예상 시
- SQLite → PostgreSQL 전환 후 replica 2+ 가능

---

## 롤백

```bash
# 이전 버전으로 롤백
oc rollout undo deploy/cafe-api -n cafe-system

# 특정 리비전으로 롤백
oc rollout undo deploy/cafe-api -n cafe-system --to-revision=3

# 롤백 히스토리
oc rollout history deploy/cafe-api -n cafe-system
```

---

## 연락처

| 역할 | 담당자 | 연락처 |
|------|--------|--------|
| 1차 대응 | 박준호 | Slack: @junho.park |
| 2차 대응 | 김민수 | Slack: @minsu.kim |
| 서비스 오너 | 인프라팀장 | Slack: #infra-team |
