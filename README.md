# The Herbwitch's Apprentice (허브마녀의 수습생 아이린) - 로컬 웹 챗봇 🌿🔮✨

동화풍 삽화와 빅토리안 앤틱 골드 & 로열 페리윙클 블루 디자인을 테마로 한 **수습 허브마녀 '아이린(Ireen)' AI 챗봇** 서비스입니다.  
Google **Gemini 3.8 Flash** 및 **Gemini 7.3 Flash**를 기반으로 하며, 실시간 인터넷 검색(Google Search Grounding)과 다정한 허브마녀 페르소나를 탑재했습니다.  
로컬 PC 환경 및 **구글 클라우드 플랫폼(GCP) Compute Engine** 가상 머신(VM)에 손쉽게 배포할 수 있습니다.

---

## 🌟 주요 기능

- **🌿 수습 허브마녀 '아이린' 페르소나 탑재**:
  - 'The Herbwitch's Apprentice' 세계관의 맑은 사파이어 눈동자와 꽃 머리장식을 한 지혜로운 마녀의 제자
  - 다정하고 따뜻한 어조로 약초학, 코딩/클라우드, 과학, 일상 지혜까지 친절하고 깊이 있게 답변
- **🎨 로열 페리윙클 & 앤틱 골드 필리그리 디자인**:
  - 원작 도서 커버의 아치형 빅토리안 금빛 프레임과 백조, 크리스탈, 허브 솥 모티프 적용
  - 세련된 세리프 폰트(`Cinzel`, `Gowun Batang`)와 수채화풍 캐릭터 일러스트레이션 연동
- **🔮 지혜의 수정구 (Google 실시간 웹 검색)**:
  - 실시간 날씨, 최신 뉴스, 실시간 트렌드 등 최신 웹 정보를 Google 검색과 연동하여 답변
  - 인용된 실제 웹 문서 출처 링크(Web Sources) 칩 카드 자동 표시
  - 원클릭으로 수정구 탐색 On/Off 토글 지원
- **⚡ Gemini 3.8 Flash 기본 탑재**: 최신 초고속 경량 플래시 모델 기반의 즉각적인 실시간 스트리밍
- **🔄 다양한 마법 영감(AI 모델) 실시간 전환**:
  - `gemini-3.8-flash` (기본값 / 초고속 영감)
  - `gemini-7.3-flash` (사용자 지정 모델)
  - `gemini-3.7-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`
- **💾 정원의 기록(세션) 자동 저장 및 양피지 내보내기**:
  - `localStorage` 기반 멀티 대화 보존 및 마크다운(`.md`) 파일 다운로드
- **⚙️ 그리모어(설정) 모달**:
  - 상상력의 온도(Temperature, 0.0 ~ 2.0), 시스템 페르소나 커스텀, 실시간 검색 설정
- **🔐 안전한 환경변수 연동**: API 키를 클라이언트에 노출하지 않고 서버 측 환경변수(`GEMINI_API_KEY`)로만 안전하게 통신

---

## 📂 프로젝트 구조

```text
gcp_compute_engine_chatbot/
├── .env.example          # 환경변수 설정 예시 템플릿
├── .gitignore            # Git 제외 목록 (API 키 및 캐시 보호)
├── LICENSE               # MIT 라이선스
├── README.md             # 프로젝트 안내 문서
├── requirements.txt      # Python 의존성 패키지 목록
├── run.bat               # Windows 간편 실행 스크립트 (원클릭 시작)
├── app.py                # Flask 백엔드 및 Gemini SSE 스트리밍 서버
├── templates/
│   └── index.html        # 시맨틱 챗봇 웹 인터페이스
└── static/
    ├── css/
    │   └── style.css     # 다크 글래스모피즘 디자인 시스템 스타일시트
    └── js/
        └── chat.js       # SSE 수신, 마크다운 렌더링 및 세션 관리 로직
```

---

## 🚀 빠른 시작 가이드 (로컬 PC)

### 1. 필수 요구사항
- Python 3.9 이상
- Google Gemini API 키 ([Google AI Studio](https://aistudio.google.com/)에서 무료 발급 가능)

### 2. 저장소 복제 (Clone)
```bash
git clone https://github.com/YOUR_USERNAME/gcp_compute_engine_chatbot.git
cd gcp_compute_engine_chatbot
```

### 3. API 키 설정

#### 방법 A: 시스템 환경변수에 등록 (권장)
- **Windows (PowerShell)**:
  ```powershell
  [System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', '발급받은_API_키', 'User')
  ```
- **Linux / macOS**:
  ```bash
  export GEMINI_API_KEY="발급받은_API_키"
  ```

#### 방법 B: `.env` 파일 생성
`.env.example` 파일을 복사하여 `.env`를 생성하고 키를 입력합니다:
```bash
cp .env.example .env
```
`.env` 파일 내용:
```env
GEMINI_API_KEY=AIzaSy...
```

### 4. 실행하기

#### Windows 사용자
- 프로젝트 폴더의 **`run.bat`** 파일을 더블 클릭하면 자동으로 패키지 확인 후 서버가 실행되고 브라우저가 열립니다.

#### 수동 실행 (터미널 / 콘솔)
```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python app.py
```

서버 구동 후 웹 브라우저에서 **`http://localhost:5000`**에 접속합니다.

---

## ☁️ GCP Compute Engine 배포 가이드

구글 클라우드 플랫폼(GCP) Compute Engine 인스턴스에 배포하여 24시간 상시 운영할 수 있습니다.

### 1. Compute Engine VM 인스턴스 생성
- OS: Ubuntu 22.04 LTS 또는 Debian 11/12
- 방화벽: **HTTP 트래픽 허용** 및 커스텀 포트(예: 5000) 방화벽 규칙 추가

### 2. VM 접속 및 패키지 설치
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git
git clone https://github.com/YOUR_USERNAME/gcp_compute_engine_chatbot.git
cd gcp_compute_engine_chatbot

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 환경변수 설정
```bash
echo 'export GEMINI_API_KEY="당신의_API_키"' >> ~/.bashrc
source ~/.bashrc
```

### 4. systemd 서비스 등록 (백그라운드 상시 실행)
`/etc/systemd/system/gemini-chatbot.service` 파일 생성:
```ini
[Unit]
Description=Gemini Chatbot Web Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/gcp_compute_engine_chatbot
Environment="GEMINI_API_KEY=당신의_API_키"
Environment="PORT=5000"
ExecStart=/home/ubuntu/gcp_compute_engine_chatbot/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 시작 및 활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl start gemini-chatbot
sudo systemctl enable gemini-chatbot
```

이제 VM의 **외부 IP 주소 (`http://<VM_EXTERNAL_IP>:5000`)**를 통해 언제 어디서나 챗봇을 이용할 수 있습니다.

---

## 📜 라이선스 (License)

이 프로젝트는 [MIT License](LICENSE)에 따라 자유롭게 사용, 수정 및 배포할 수 있습니다.
