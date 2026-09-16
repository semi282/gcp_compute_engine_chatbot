# GCP Compute Engine 인스턴스 생성 및 챗봇 배포 실시간 로그

**배포 일시**: 2026-09-15 15:08:00 (HTTPS 보안 전환 완료: 15:48:00)  
**대상 프로젝트 ID**: `iceu-songpa16` (프로젝트 번호: `352439210179`)  
**리전 / 존**: `us-central1` / `us-central1-a` (주피터 노트북 비용 분석 기준 전 세계 최저가 1위 리전)  
**머신 유형**: `e2-medium` (2 vCPU, 4GB RAM, 10GB pd-balanced 부팅 디스크, Debian 12 GNU/Linux)  
**Secret Manager 연동**: `projects/352439210179/secrets/GEMINI_API_KEY` (인스턴스 메타데이터 IAM 인증 기반 자동 주입)  
**보안 공인 HTTPS URL**: **[https://136-65-198-112.sslip.io](https://136-65-198-112.sslip.io)** (Let's Encrypt 공인 인증서 탑재)  
**표준 IP HTTPS URL**: **[https://136.65.198.112](https://136.65.198.112)** (포트 번호 없이 바로 접속)

---

## 📜 실시간 배포 진행 내역

### 1. 환경 초기화 및 계정 인증
- `2026-09-15 15:08:00` : GCP Compute Engine 배포 오케스트레이션 시작
- `2026-09-15 15:08:00` : OAuth2 액세스 토큰 갱신 성공 및 `CLOUDSDK_AUTH_ACCESS_TOKEN` 환경변수 주입 완료
- `2026-09-15 15:08:02` : GCP 대상 프로젝트 활성화 확인: `iceu-songpa16`

### 2. Secret Manager IAM 권한 설정
- `2026-09-15 15:08:02` : Secret Manager IAM 접근 권한 확인
- `2026-09-15 15:08:02` : Compute Engine 기본 서비스 계정(`352439210179-compute@developer.gserviceaccount.com`)에 `roles/secretmanager.secretAccessor` 역할 바인딩
- `2026-09-15 15:08:05` : ✔ Secret Manager IAM 권한 바인딩 성공

### 3. VPC 방화벽 규칙 구성
- `2026-09-15 15:08:05` : VPC 방화벽 규칙 `allow-chatbot-5000` 확인
- `2026-09-15 15:08:08` : ✔ 방화벽 규칙 확인 완료 (TCP 5000 및 80 인바운드 트래픽 허용, 대상 태그: `chatbot-server`)

### 4. Compute Engine 인스턴스 프로비저닝
- `2026-09-15 15:08:08` : Compute Engine 인스턴스 `instance-chatbot-us-central1` 프로비저닝 확인
- `2026-09-15 15:08:10` : ✔ 인스턴스 `instance-chatbot-us-central1` 정상 생성 및 실행 상태 확인 (`RUNNING`)
- `2026-09-15 15:08:10` : 부트스트랩 `startup-script` 자동 실행 (Debian 12 시스템 패키지, Python 가상환경 구성, Secret Manager 키 취득)

### 5. 네트워크 주소 획득
- `2026-09-15 15:08:10` : 인스턴스 공용 외부 IP (External NAT IP) 조회
- `2026-09-15 15:08:13` : 🌟 공용 외부 IP 할당 완료: `136.65.198.112`

### 6. 애플리케이션 코드 패키징 및 업로드
- `2026-09-15 15:08:13` : 챗봇 소스 코드 압축 패키징 (`bundle.tar.gz`) 진행 (`app.py`, `requirements.txt`, `templates/`, `static/`, `scripts/`)
- `2026-09-15 15:08:13` : ✔ 소스 코드 패키징 완료: `bundle.tar.gz` (903.8 KB)
- `2026-09-15 15:08:17` : ✔ VM SSH 포트 22 연결 준비 완료
- `2026-09-15 15:08:17` : `gcloud compute scp`를 통해 `instance-chatbot-us-central1:/tmp/bundle.tar.gz`로 전송
- `2026-09-15 15:08:26` : ✔ 소스 코드 아카이브 VM 전송 완료

### 7. 원격 서버 배포 및 systemd 서비스 기동
- `2026-09-15 15:08:26` : 원격 `/opt/chatbot` 디렉터리에 코드 아카이브 압축 해제
- `2026-09-15 15:08:30` : Python 3 가상환경(`venv`) 내 종속성 설치 (`flask`, `google-genai`, `requests`, `python-dotenv`)
- `2026-09-15 15:08:35` : `/etc/systemd/system/chatbot.service` 등록 및 `systemctl daemon-reload`
- `2026-09-15 15:08:40` : `systemctl enable --now chatbot.service` 실행
- `2026-09-15 15:08:42` : ✔ 원격 챗봇 서비스 설치 및 systemd 기동 성공 (서비스 상태: `active (running)`)

### 8. 서비스 검증 및 Secret Manager 연동 확인
- `2026-09-15 15:08:50` : 클라우드 서비스 상태 엔드포인트(`http://136.65.198.112:5000/api/status`) 헬스체크 수행 (HTTP 200 OK)
- `2026-09-15 15:09:50` : 원격 VM 스트리밍 대화 API E2E 테스트 수행 완료

### 9. 회원가입/로그인 기능 클라우드 갱신 배포
- `2026-09-15 15:29:27` : SQLite 내장 데이터베이스 기반 회원가입, 로그인, 세션 동기화 기능 배포
- `2026-09-15 15:29:43` : ✔ 원격 회원가입(`cloud_apprentice`), 로그인, 세션 상태 확인 E2E 검증 통과

### 10. HTTPS(SSL/TLS) 전환 및 Nginx 리버스 프록시 구축
- `2026-09-15 15:44:57` : HTTP -> HTTPS 전환 시작
- `2026-09-15 15:45:06` : ✔ GCP VPC 방화벽 규칙 갱신: TCP 443 (HTTPS) 추가 허용 (`allow-chatbot-5000` -> `tcp:5000,tcp:80,tcp:443`)
- `2026-09-15 15:45:12` : ✔ 인스턴스 태그 `https-server` 추가 완료
- `2026-09-15 15:45:45` : Flask 내부 포트를 5001로 배치하고 Nginx 리버스 프록시로 포트 80, 443, 5000 바인딩
- `2026-09-15 15:46:30` : ✔ Nginx 고성능 리버스 프록시 및 OpenSSL 2048비트 SAN SSL 인증서 탑재
- `2026-09-15 15:47:27` : ✔ Certbot(Let's Encrypt) 공인 CA 인증서 자동 발급 및 배포 완료 (`136-65-198-112.sslip.io`)

### 11. HTTPS 보안 접속 및 암호화 스트리밍 검증
- `2026-09-15 15:47:35` : ✔ 공인 CA 신뢰 HTTPS 검증: `https://136-65-198-112.sslip.io/api/status` (HTTP 200 OK, 브라우저 보안 경고 없음)
- `2026-09-15 15:47:40` : ✔ 표준 HTTPS(포트 443) 상태 확인: `https://136.65.198.112/api/status` (HTTP 200 OK)
- `2026-09-15 15:47:42` : ✔ 기존 5000 포트 HTTPS 호환성 확인: `https://136.65.198.112:5000/api/status` (HTTP 200 OK)
- `2026-09-15 15:48:15` : ✔ HTTP -> HTTPS 자동 보안 리다이렉트 확인 (`http://136-65-198-112.sslip.io` -> `301 Moved Permanently`)
- `2026-09-15 15:48:05` : ✔ HTTPS 보안 채널 상에서 Server-Sent Events (SSE) 실시간 AI 스트리밍 대화 수신 성공 (`proxy_buffering off`)

### 12. 클라우드 자원 및 과금 요소 완전 삭제 (Clean-up)
- `2026-09-15 16:13:40` : 사용자 요청에 따른 GCP 과금 유발 자원 정리 시작
- `2026-09-15 16:13:44` : ✔ Compute Engine VM 인스턴스 `instance-chatbot-us-central1` 및 연결된 부팅 디스크(10GB) 영구 삭제 완료
- `2026-09-15 16:13:44` : ✔ VPC 방화벽 규칙 `allow-chatbot-5000` 삭제 완료
- `2026-09-15 16:14:00` : ✔ 인스턴스, 디스크, 고정 IP, 스냅샷 등 잔여 과금 자원 전수 검증 결과: **0개 (추가 과금 발생 요인 완전 차단)**

---

## 🔒 최종 자원 상태 정보

| 항목 | 상태 | 설명 |
| :--- | :--- | :--- |
| **Compute Engine 인스턴스** | **삭제 완료 (TERMINATED / 0개)** | VM 가동 중단 및 인스턴스 리소스 반환 |
| **영구 부팅 디스크 (pd-balanced)**| **삭제 완료 (DELETED / 0개)** | 10GB 스토리지 볼륨 삭제로 디스크 과금 방지 |
| **정적 IP 주소 (Static IP)** | **할당 없음 (0개)** | 미사용 정적 IP 과금 없음 |
| **스냅샷 & 리소스 정책** | **0개** | 백업 스토리지 과금 없음 |
| **GCP VPC 방화벽 규칙** | **`allow-chatbot-5000` 삭제 완료** | 기본 방화벽 규칙만 유지 |
| **최종 과금 상태** | **✔ CLEAN (과금 발생 요인 전면 해제)** | 추가 클라우드 비용 발생 원천 차단 |

