import os
import json
import re
import sqlite3
import requests
from flask import Flask, render_template, request, Response, jsonify, stream_with_context, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "herbwitch_secret_key_2026_ireen_apprentice_secure_moonlight"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# SQLite Database Setup
DB_PATH = os.path.join(app.instance_path, "chatbot.db")
os.makedirs(app.instance_path, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                nickname TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'apprentice',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

init_db()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

AVAILABLE_MODELS = [
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash (기본값)",
        "badge": "Default / Ultra-fast",
        "description": "최신 고성능 멀티모달 플래시 모델로 빠르고 정확한 추론 제공",
        "default": True
    },
    {
        "id": "gemini-7.3-flash",
        "name": "Gemini 7.3 Flash",
        "badge": "Special",
        "description": "사용자 지정 차세대 Flash 모델 옵션 (API 가용 상태에 따라 작동)",
        "default": False
    },
    {
        "id": "gemini-3.7-flash",
        "name": "Gemini 3.7 Flash",
        "badge": "Stable",
        "description": "검증된 강력한 추론 및 코딩 보조 특화 Flash 모델",
        "default": False
    },
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "badge": "Standard",
        "description": "안정적인 표준 경량 모델",
        "default": False
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "badge": "Pro",
        "description": "복잡한 문제 해결 및 심층 분석을 위한 대규모 Pro 모델",
        "default": False
    }
]

_CACHED_SECRET_KEY = None

def get_api_key():
    global _CACHED_SECRET_KEY
    # 1. Environment variables
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    # 2. Return cached secret if already retrieved
    if _CACHED_SECRET_KEY:
        return _CACHED_SECRET_KEY

    # 3. Fallback: Retrieve from GCP Secret Manager (projects/352439210179/secrets/GEMINI_API_KEY)
    secret_path = os.environ.get("GCP_SECRET_NAME", "projects/352439210179/secrets/GEMINI_API_KEY/versions/latest")
    
    # Try Google Cloud Python SDK if installed
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(name=secret_path)
        _CACHED_SECRET_KEY = response.payload.data.decode("utf-8").strip()
        print("[Auth] Retrieved GEMINI_API_KEY from GCP Secret Manager (SDK)")
        return _CACHED_SECRET_KEY
    except Exception:
        pass

    # Try GCP Compute Engine metadata server token + REST API
    try:
        token_resp = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
            timeout=2
        )
        if token_resp.status_code == 200:
            token = token_resp.json().get("access_token")
            if not secret_path.endswith(":access") and "/versions/" not in secret_path:
                url = f"https://secretmanager.googleapis.com/v1/{secret_path}/versions/latest:access"
            elif not secret_path.endswith(":access"):
                url = f"https://secretmanager.googleapis.com/v1/{secret_path}:access"
            else:
                url = f"https://secretmanager.googleapis.com/v1/{secret_path}"

            s_resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if s_resp.status_code == 200:
                import base64
                data_b64 = s_resp.json().get("payload", {}).get("data", "")
                _CACHED_SECRET_KEY = base64.b64decode(data_b64).decode("utf-8").strip()
                print("[Auth] Retrieved GEMINI_API_KEY from GCP Secret Manager (REST)")
                return _CACHED_SECRET_KEY
    except Exception:
        pass

    return ""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    api_key = get_api_key()
    has_key = bool(api_key.strip())
    masked_key = ""
    if has_key:
        if len(api_key) > 10:
            masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        else:
            masked_key = "***"
    return jsonify({
        "status": "online",
        "has_api_key": has_key,
        "masked_key": masked_key,
        "default_model": "gemini-3.8-flash"
    })

@app.route("/api/models")
def get_models():
    return jsonify({
        "models": AVAILABLE_MODELS
    })

# ==========================================
# Authentication & User Management Endpoints
# ==========================================

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(force=True) or {}
    username = str(data.get("username", "")).strip().lower()
    nickname = str(data.get("nickname", "")).strip()
    password = str(data.get("password", "")).strip()

    # Validation
    if not username or not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        return jsonify({
            "success": False,
            "message": "아이디는 3~20자의 영문, 숫자, 밑줄(_)만 사용 가능합니다."
        }), 400

    if not nickname or len(nickname) < 2 or len(nickname) > 20:
        return jsonify({
            "success": False,
            "message": "수습생 칭호(닉네임)는 2~20자 사이여야 합니다."
        }), 400

    if not password or len(password) < 6:
        return jsonify({
            "success": False,
            "message": "마법 암호(비밀번호)는 최소 6자 이상이어야 합니다."
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, nickname, password_hash) VALUES (?, ?, ?)",
                (username, nickname, password_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()

        session["user_id"] = user_id
        return jsonify({
            "success": True,
            "message": f"어서 오세요! 수습생 '{nickname}' 님의 입회가 승인되었습니다. ✨",
            "user": {
                "id": user_id,
                "username": username,
                "nickname": nickname,
                "role": "apprentice"
            }
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "message": "이미 마법 서고에 등록된 수습생 아이디입니다."
        }), 409
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"입회 처리 중 오류가 발생했습니다: {str(e)}"
        }), 500

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(force=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "아이디와 마법 암호를 모두 입력해주세요."
        }), 400

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, nickname, password_hash, role FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({
            "success": False,
            "message": "아이디 또는 마법 암호가 일치하지 않습니다."
        }), 401

    session["user_id"] = user["id"]
    return jsonify({
        "success": True,
        "message": f"반가워요, 수습생 {user['nickname']} 님! 약초 공방에 오신 것을 환영해요. 🌿",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "nickname": user["nickname"],
            "role": user["role"]
        }
    })

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.pop("user_id", None)
    return jsonify({
        "success": True,
        "message": "안전하게 서재에서 물러났습니다. 평온한 시간 되세요!"
    })

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({
            "authenticated": False,
            "user": None
        })

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, nickname, role FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

    if not user:
        session.pop("user_id", None)
        return jsonify({
            "authenticated": False,
            "user": None
        })

    return jsonify({
        "authenticated": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "nickname": user["nickname"],
            "role": user["role"]
        }
    })

@app.route("/api/user/sessions", methods=["GET"])
def get_user_sessions():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"sessions": []})

    with get_db() as conn:
        sessions_rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        ).fetchall()

        result = []
        for s in sessions_rows:
            msgs = conn.execute(
                "SELECT role, content, sources, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
                (s["id"],)
            ).fetchall()
            
            message_list = []
            for m in msgs:
                sources = []
                if m["sources"]:
                    try:
                        sources = json.loads(m["sources"])
                    except Exception:
                        pass
                message_list.append({
                    "role": m["role"],
                    "content": m["content"],
                    "sources": sources,
                    "timestamp": m["created_at"]
                })

            result.append({
                "id": s["id"],
                "title": s["title"],
                "updatedAt": s["updated_at"],
                "messages": message_list
            })

    return jsonify({"sessions": result})

@app.route("/api/user/sessions/sync", methods=["POST"])
def sync_user_sessions():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json(force=True) or {}
    sessions_data = data.get("sessions", [])

    with get_db() as conn:
        for s in sessions_data:
            session_id = s.get("id")
            title = s.get("title", "달빛 아래 새로운 이야기")
            messages = s.get("messages", [])
            
            if not session_id:
                continue

            conn.execute("""
                INSERT INTO chat_sessions (id, user_id, title, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET title = excluded.title, updated_at = CURRENT_TIMESTAMP
            """, (session_id, user_id, title))

            # Replace messages for this session
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                sources_json = json.dumps(m.get("sources", []), ensure_ascii=False) if m.get("sources") else None
                conn.execute("""
                    INSERT INTO chat_messages (session_id, role, content, sources)
                    VALUES (?, ?, ?, ?)
                """, (session_id, role, content, sources_json))
        conn.commit()

    return jsonify({"success": True, "message": "서재에 안전하게 동기화되었습니다."})

@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    api_key = get_api_key()
    if not api_key:
        def err_gen():
            error_data = {
                "error": True,
                "message": "GEMINI_API_KEY 환경변수가 설정되지 않았습니다. PC 환경변수 또는 .env 파일에 GEMINI_API_KEY를 등록해주세요."
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return Response(stream_with_context(err_gen()), mimetype="text/event-stream")

    data = request.get_json(force=True) or {}
    model = data.get("model", "gemini-3.8-flash").strip()
    raw_messages = data.get("messages", [])
    system_instruction = data.get("system_instruction", "").strip()
    temperature = float(data.get("temperature", 0.7))
    web_search = bool(data.get("web_search", True))

    # Format messages for Gemini API
    # Role mapping: 'assistant' -> 'model', 'user' -> 'user'
    formatted_contents = []
    for msg in raw_messages:
        role = "model" if msg.get("role") in ["assistant", "model"] else "user"
        content = msg.get("content", "").strip()
        if content:
            formatted_contents.append({
                "role": role,
                "parts": [{"text": content}]
            })

    if not formatted_contents:
        def empty_gen():
            error_data = {"error": True, "message": "전송할 메시지가 비어있습니다."}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return Response(stream_with_context(empty_gen()), mimetype="text/event-stream")

    payload = {
        "contents": formatted_contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192
        }
    }

    DEFAULT_CHARACTER_INSTRUCTION = (
        "당신은 'The Herbwitch's Apprentice'의 지혜로운 수습 허브마녀 '아이린(Ireen)'입니다. "
        "맑은 사파이어 눈동자와 꽃 머리장식을 한 다정하고 총명한 마녀의 제자입니다. "
        "사용자를 '여행자님' 또는 친근하고 다정한 경어체(~해요, ~랍니다, ~이에요)로 부드럽게 맞이합니다. "
        "프로그래밍, GCP 클라우드, 과학, 철학, 허브와 건강 등 사용자의 모든 질문에 대해 깊이 있고 매우 정확한 전문 지식을 친절하게 제공하며, "
        "실시간 웹 검색 결과는 '지혜의 수정구로 세상의 기록을 비추어 보았어요'처럼 자연스럽고 매력적인 톤으로 전해줍니다."
    )

    active_instruction = system_instruction if system_instruction else DEFAULT_CHARACTER_INSTRUCTION
    payload["systemInstruction"] = {
        "parts": [{"text": active_instruction}]
    }

    # Enable Google Search Grounding for real-time web search
    if web_search:
        payload["tools"] = [{"googleSearch": {}}]

    gemini_url = f"{GEMINI_API_BASE}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"

    def event_stream():
        try:
            with requests.post(
                gemini_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=60
            ) as response:
                if response.status_code != 200:
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error", {}).get("message", response.text)
                    except Exception:
                        err_msg = response.text or f"HTTP {response.status_code}"

                    # Custom guidance for 404
                    if response.status_code == 404:
                        suggestion = ""
                        if "gemini-7.3" in model:
                            suggestion = " (현재 Google API에서는 'gemini-3.8-flash' 또는 'gemini-3.7-flash'가 활성화되어 있습니다. 상단 모델 선택기에서 Gemini 3.8 Flash를 선택해보세요.)"
                        friendly_msg = f"API 모델 호출 실패 (404 Not Found): '{model}' 모델을 현재 API 버전에서 찾을 수 없습니다.{suggestion}\n\n[Google API 상세 에러]: {err_msg}"
                    elif response.status_code == 400:
                        friendly_msg = f"잘못된 요청 형식 (400 Bad Request): {err_msg}"
                    elif response.status_code in (401, 403):
                        friendly_msg = f"인증 실패 ({response.status_code}): 등록된 GEMINI_API_KEY를 확인해주세요. ({err_msg})"
                    else:
                        friendly_msg = f"Google API 오류 ({response.status_code}): {err_msg}"

                    yield f"data: {json.dumps({'error': True, 'message': friendly_msg}, ensure_ascii=False)}\n\n"
                    return

                # Read raw bytes and decode as UTF-8 properly without ISO-8859-1 splitting issues
                buffer = ""
                seen_queries = []
                seen_uris = set()
                collected_sources = []

                for chunk in response.iter_content(chunk_size=1024, decode_unicode=False):
                    if not chunk:
                        continue
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if not data_str:
                            continue
                        try:
                            chunk_json = json.loads(data_str)
                            candidates = chunk_json.get("candidates", [])
                            if candidates:
                                cand = candidates[0]
                                parts = cand.get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        chunk_payload = {
                                            "error": False,
                                            "text": text,
                                            "finishReason": cand.get("finishReason")
                                        }
                                        yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"

                                # Extract Grounding (Web Search metadata)
                                grounding = cand.get("groundingMetadata")
                                if grounding:
                                    has_new_grounding = False
                                    queries = grounding.get("webSearchQueries", [])
                                    for q in queries:
                                        if q and q not in seen_queries:
                                            seen_queries.append(q)
                                            has_new_grounding = True
                                    chunks = grounding.get("groundingChunks", [])
                                    for c in chunks:
                                        web = c.get("web")
                                        if web and web.get("uri"):
                                            uri = web.get("uri")
                                            title = web.get("title") or "웹 검색 결과"
                                            if uri not in seen_uris:
                                                seen_uris.add(uri)
                                                collected_sources.append({"title": title, "uri": uri})
                                                has_new_grounding = True
                                    if has_new_grounding:
                                        yield f"data: {json.dumps({'grounding': {'queries': seen_queries, 'sources': collected_sources}}, ensure_ascii=False)}\n\n"

                        except json.JSONDecodeError:
                            continue

                # Signal stream completion with final grounding info if any
                yield f"data: {json.dumps({'done': True, 'grounding': {'queries': seen_queries, 'sources': collected_sources}}, ensure_ascii=False)}\n\n"

        except requests.exceptions.Timeout:
            yield f"data: {json.dumps({'error': True, 'message': 'Google Gemini API 요청 시간이 초과되었습니다.'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': True, 'message': f'스트리밍 중 예외 발생: {str(e)}'}, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"==================================================")
    print(f" Gemini Chatbot Server Started")
    print(f" Local URL: http://localhost:{port}")
    print(f" GEMINI_API_KEY Configured: {bool(get_api_key())}")
    print(f" Default Model: gemini-3.8-flash")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
