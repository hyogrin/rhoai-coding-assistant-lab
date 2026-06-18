# Cafe Order System — Security Policy

## 보안 등급

본 시스템은 **내부 일반** 등급으로 분류됩니다.
사내망(VPN) 내에서만 접근 가능하며, 개인식별정보(PII) 처리는 최소화합니다.

## 데이터 분류

| 데이터 | 등급 | 보호 방법 |
|--------|------|-----------|
| 직원 사번 | 내부 | 평문 저장 (사내 공개 정보) |
| 직원 이메일 | 내부 | 평문 저장 |
| 주문 내역 | 내부 | 6개월 보관 후 아카이브 |
| 결제 정보 | N/A | 본 시스템에서 처리하지 않음 (복지포인트 시스템 연동) |

## 네트워크 보안

### 접근 제어
- OpenShift Route에 `NetworkPolicy` 적용
- 사내 IP 대역(10.0.0.0/8)에서만 접근 허용
- TLS 종단: OpenShift Router에서 처리 (edge termination)

### Pod Security
```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
```

## 인증/인가

### 현재 (v1.2)
- 인증 없음 (사내망 신뢰 모델)
- 모든 API가 공개

### 계획 (v2.0)
- OpenShift OAuth Proxy를 통한 SSO 연동
- RBAC 적용:
  - `customer` 역할: 자신의 주문만 생성/조회
  - `barista` 역할: 주문 상태 변경
  - `admin` 역할: 메뉴 관리, 고객 관리

## 취약점 관리

### 컨테이너 이미지
- UBI(Universal Base Image) 기반으로 빌드
- Quay.io 보안 스캔 통과 필수
- 매월 1회 이미지 재빌드 (보안 패치 적용)

### 의존성
- `pip-audit` 를 CI 파이프라인에 포함
- CRITICAL/HIGH 취약점 발견 시 3일 내 패치

## 로깅 및 감사

### 수집 로그
- API 요청/응답 (본문 제외, 메타데이터만)
- 주문 상태 변경 이벤트
- 에러/예외 발생 이벤트

### 보관 정책
- 애플리케이션 로그: 30일
- 감사 로그: 1년

## 인시던트 대응

1. 보안 이슈 발견 시 `#infra-security` Slack 채널에 즉시 보고
2. 담당자: 인프라팀 박준호 (EMP003)
3. 심각도에 따라 4시간/24시간/72시간 내 대응

## 컴플라이언스

- 개인정보보호법: 직원 동의 하에 최소 정보만 수집
- 사내 정보보안 지침 v3.2 준수
- 연 1회 보안 점검 대상
