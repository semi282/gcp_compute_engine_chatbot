# 🚀 GCP Compute Engine 챗봇 서비스 패키지 (`compute_engine`)

본 디렉터리는 **GCP Compute Engine** 환경에 배포 및 가동되는 The Herbwitch's Apprentice (허브마녀의 수습생 아이린) 챗봇 웹 애플리케이션 및 인프라 오케스트레이션 스크립트를 포함하고 있습니다.

---

## 📂 패키지 구성 요약

- **`app.py`**: Flask 백엔드 코어 (Google Gemini API SSE 실시간 스트리밍, SQLite 회원 인증/대화 세션, GCP Secret Manager 연동)
- **`requirements.txt`**: 파이썬 종속 라이브러리 목록 (`flask`, `google-genai`, `requests`, `python-dotenv` 등)
- **`run.bat`**: Windows 환경 로컬 개발 서버 원클릭 실행 스크립트
- **`.env.example`**: 로컬 테스트용 환경변수 템플릿 (`GEMINI_API_KEY`)
- **`compute_engine_example.ipynb`**: GCP Compute Engine 글로벌 리전별 비용 분석 및 e2-medium 프로비저닝 노트북
- **`deployment_log.md`**: GCP 배포 이력 및 인프라 상태 로그
- **`instance/`**: SQLite3 데이터베이스 로컬 디렉터리 (`chatbot.db`)
- **`scripts/`**:
  - `deploy_to_gcp.py`: GCP 인스턴스 생성, 방화벽(TCP 443, 80, 5000), 소스 압축(`bundle.tar.gz`) 업로드 및 원격 systemd 기동을 자동 수행하는 Python 오케스트레이터
  - `startup.sh`: GCP Compute Engine VM 부팅 시 인스턴스 메타데이터를 통해 Secret Manager에서 API 키를 안전하게 가져오고 환경을 구성하는 부트스트랩 스크립트
  - `setup_https.sh`: Nginx 리버스 프록시(포트 443/80/5000 -> 포트 5001 프록시) 설치, OpenSSL SAN SSL 및 Let's Encrypt 공인 인증서 자동 발급 스크립트
  - `chatbot.service`: Linux `systemd` 상시 가동 백그라운드 서비스 정의 파일
- **`templates/`**: 웹 프론트엔드 UI 템플릿 (`index.html`)
- **`static/`**: 정적 리소스 (`css/style.css`, `js/chat.js`, `img/*`)

---

## 💻 로컬 실행 방법

```bash
cd compute_engine
pip install -r requirements.txt
python app.py
```
또는 Windows에서 `run.bat`을 더블 클릭합니다.

---

## ☁️ GCP 클라우드 배포 실행

```bash
python scripts/deploy_to_gcp.py
```
배포 스크립트는 본 디렉터리(`compute_engine`)의 소스를 패키징하여 Compute Engine 인스턴스(`/opt/chatbot`)에 자동 전송 및 배포합니다.
