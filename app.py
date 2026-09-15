import os
import json
import requests
from flask import Flask, render_template, request, Response, jsonify, stream_with_context
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

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

def get_api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

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
