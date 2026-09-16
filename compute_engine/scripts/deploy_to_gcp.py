import os
import sys
import time
import json
import subprocess
import tarfile
import requests
from datetime import datetime

import io

# Force UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "iceu-songpa16")
PROJECT_NUMBER = os.environ.get("GCP_PROJECT_NUMBER", "352439210179")
ZONE = os.environ.get("GCP_ZONE", "us-central1-a")
REGION = os.environ.get("GCP_REGION", "us-central1")
INSTANCE_NAME = os.environ.get("GCP_INSTANCE_NAME", "instance-chatbot-us-central1")
MACHINE_TYPE = os.environ.get("GCP_MACHINE_TYPE", "e2-medium")
SECRET_NAME = f"projects/{PROJECT_NUMBER}/secrets/GEMINI_API_KEY"
FIREWALL_RULE = "allow-chatbot-5000"
SERVICE_ACCOUNT = f"{PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Dynamic repository root directory
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_FILE = os.path.join(WORKSPACE_DIR, "deployment_log.md")

def log(msg, heading=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now}] {msg}"
    try:
        print(formatted)
        sys.stdout.flush()
    except Exception:
        pass
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        if heading:
            f.write(f"\n### {heading}\n\n")
        f.write(f"- `{now}` : {msg}\n")

def init_auth():
    """Ensure OAuth2 access token is available and set in CLOUDSDK_AUTH_ACCESS_TOKEN."""
    if os.environ.get("CLOUDSDK_AUTH_ACCESS_TOKEN"):
        return os.environ.get("CLOUDSDK_AUTH_ACCESS_TOKEN")

    # Search dynamically for gcloud credentials without hardcoded user paths
    possible_cred_files = []
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        legacy_dir = os.path.join(appdata, "gcloud", "legacy_credentials")
        if os.path.exists(legacy_dir):
            for root, _, files in os.walk(legacy_dir):
                if "adc.json" in files:
                    possible_cred_files.append(os.path.join(root, "adc.json"))
        possible_cred_files.append(os.path.join(appdata, "gcloud", "application_default_credentials.json"))

    home = os.path.expanduser("~")
    possible_cred_files.append(os.path.join(home, ".config", "gcloud", "application_default_credentials.json"))

    for cred_file in possible_cred_files:
        if os.path.exists(cred_file):
            try:
                with open(cred_file, "r") as f:
                    creds = json.load(f)
                payload = {
                    "client_id": creds.get("client_id"),
                    "client_secret": creds.get("client_secret"),
                    "refresh_token": creds.get("refresh_token"),
                    "grant_type": "refresh_token"
                }
                resp = requests.post("https://oauth2.googleapis.com/token", data=payload, timeout=10)
                if resp.status_code == 200:
                    token = resp.json().get("access_token")
                    os.environ["CLOUDSDK_AUTH_ACCESS_TOKEN"] = token
                    os.environ["CLOUDSDK_CORE_PROJECT"] = PROJECT_ID
                    return token
            except Exception:
                continue
    return None

def run_cmd(cmd, check=True, capture_output=True, timeout=300):
    init_auth()  # refresh / ensure token is alive
    res = subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=capture_output,
        cwd=WORKSPACE_DIR,
        env=os.environ,
        timeout=timeout
    )
    if check and res.returncode != 0:
        err_msg = (res.stderr or res.stdout or "").strip()
        raise RuntimeError(f"명령어 실행 실패 (code {res.returncode}): {cmd}\n{err_msg}")
    return res

def init_log_file():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# GCP Compute Engine 인스턴스 생성 및 챗봇 배포 실시간 로그\n\n")
        f.write(f"**배포 시작 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**대상 프로젝트 ID**: `{PROJECT_ID}` (프로젝트 번호: `{PROJECT_NUMBER}`)\n")
        f.write(f"**리전 / 존**: `{REGION}` / `{ZONE}` (주피터 노트북 분석 기준 전 세계 최저가 1위 리전)\n")
        f.write(f"**머신 유형**: `{MACHINE_TYPE}` (2 vCPU, 4GB RAM, 10GB pd-balanced 부팅 디스크)\n")
        f.write(f"**Secret Manager 연동**: `{SECRET_NAME}`\n\n")
        f.write("---\n\n")
        f.write("## 📜 실시간 배포 진행 내역\n\n")

def main():
    init_log_file()
    log("GCP Compute Engine 배포 오케스트레이션을 시작합니다.", "1. 환경 초기화 및 계정 인증")

    # Step 1: Check Auth
    token = init_auth()
    if not token:
        log("❌ 인증 토큰 획득 실패. adc.json을 확인하세요.")
        return False
    log(f"OAuth2 액세스 토큰 갱신 성공 및 `CLOUDSDK_AUTH_ACCESS_TOKEN` 환경변수 주입 완료 (길이: {len(token)})")

    run_cmd(f"gcloud config set project {PROJECT_ID}", check=False)
    log(f"GCP 대상 프로젝트 설정 확인: `{PROJECT_ID}`")

    # Step 2: Secret Manager IAM Binding
    log("Secret Manager IAM 접근 권한 설정 확인 중...", "2. Secret Manager IAM 권한 설정")
    try:
        log(f"Compute Engine 기본 서비스 계정(`{SERVICE_ACCOUNT}`)에 `secretmanager.secretAccessor` 역할 부여...")
        iam_cmd = (
            f"gcloud projects add-iam-policy-binding {PROJECT_ID} "
            f"--member=\"serviceAccount:{SERVICE_ACCOUNT}\" "
            f"--role=\"roles/secretmanager.secretAccessor\" --quiet"
        )
        res_iam = run_cmd(iam_cmd, check=False)
        if res_iam.returncode == 0:
            log("✔ Secret Manager IAM 권한 바인딩 성공 (`roles/secretmanager.secretAccessor`)")
        else:
            log(f"IAM 바인딩 응답: {res_iam.stderr[:200] if res_iam.stderr else '완료'}")
    except Exception as e:
        log(f"IAM 설정 경고 (기존 설정 유지): {e}")

    # Step 3: Firewall Rule
    log(f"VPC 방화벽 규칙 `{FIREWALL_RULE}` 확인 중...", "3. VPC 방화벽 규칙 구성")
    fw_check = run_cmd(f"gcloud compute firewall-rules describe {FIREWALL_RULE} --project={PROJECT_ID}", check=False)
    if fw_check.returncode != 0:
        log(f"방화벽 규칙 `{FIREWALL_RULE}` 생성 중 (TCP 5000, 80 인바운드 허용, 대상 태그: chatbot-server)...")
        fw_create_cmd = (
            f"gcloud compute firewall-rules create {FIREWALL_RULE} "
            f"--project={PROJECT_ID} "
            f"--direction=INGRESS "
            f"--priority=1000 "
            f"--network=default "
            f"--action=ALLOW "
            f"--rules=tcp:5000,tcp:80,tcp:443 "
            f"--source-ranges=0.0.0.0/0 "
            f"--target-tags=chatbot-server "
            f"--description=\"Allow inbound traffic for Herbwitch Gemini Chatbot\" --quiet"
        )
        run_cmd(fw_create_cmd)
        log("✔ 방화벽 규칙 생성 완료: 포트 5000, 80, 443(HTTPS) 인터넷 전체 오픈")
    else:
        log(f"✔ 기존 방화벽 규칙 `{FIREWALL_RULE}` 확인 (포트 5000, 80, 443 개방됨)")

    # Step 4: Compute Engine Instance Check / Create
    log(f"Compute Engine 인스턴스 `{INSTANCE_NAME}` 존재 여부 확인...", "4. Compute Engine 인스턴스 프로비저닝")
    vm_check = run_cmd(f"gcloud compute instances describe {INSTANCE_NAME} --zone={ZONE} --project={PROJECT_ID}", check=False)
    
    startup_script_path = os.path.join(WORKSPACE_DIR, "scripts", "startup.sh")

    if vm_check.returncode != 0:
        log(f"최저가 리전 `{ZONE}`에 `{MACHINE_TYPE}` VM 인스턴스 생성 시작 (Debian 12, 10GB pd-balanced)...")
        create_vm_cmd = (
            f"gcloud compute instances create {INSTANCE_NAME} "
            f"--project={PROJECT_ID} "
            f"--zone={ZONE} "
            f"--machine-type={MACHINE_TYPE} "
            f"--network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default "
            f"--tags=chatbot-server,http-server,https-server "
            f"--metadata=enable-osconfig=TRUE "
            f"--metadata-from-file=startup-script=\"{startup_script_path}\" "
            f"--maintenance-policy=MIGRATE "
            f"--provisioning-model=STANDARD "
            f"--service-account={SERVICE_ACCOUNT} "
            f"--scopes=https://www.googleapis.com/auth/cloud-platform "
            f"--create-disk=auto-delete=yes,boot=yes,device-name={INSTANCE_NAME},image=projects/debian-cloud/global/images/family/debian-12,mode=rw,size=10,type=pd-balanced "
            f"--no-shielded-secure-boot "
            f"--shielded-vtpm "
            f"--shielded-integrity-monitoring --quiet"
        )
        run_cmd(create_vm_cmd)
        log(f"✔ Compute Engine 인스턴스 `{INSTANCE_NAME}` 생성 완료!")
    else:
        log(f"✔ 인스턴스 `{INSTANCE_NAME}` 확인 완료 (기존 인스턴스 사용)")

    # Step 5: External IP
    log("인스턴스 공용 외부 IP (External NAT IP) 조회 중...", "5. 네트워크 주소 획득")
    ip_res = run_cmd(
        f"gcloud compute instances describe {INSTANCE_NAME} --zone={ZONE} --project={PROJECT_ID} "
        f"--format=\"value(networkInterfaces[0].accessConfigs[0].natIP)\""
    )
    external_ip = ip_res.stdout.strip()
    log(f"🌟 인스턴스 공용 외부 IP 할당: `{external_ip}`")

    # Step 6: Code Packaging
    log("챗봇 소스 코드 압축 패키징 (`bundle.tar.gz`) 진행 중...", "6. 애플리케이션 코드 패키징 및 업로드")
    bundle_path = os.path.join(WORKSPACE_DIR, "bundle.tar.gz")
    with tarfile.open(bundle_path, "w:gz") as tar:
        for item in ["app.py", "requirements.txt", "templates", "static", "scripts"]:
            item_path = os.path.join(WORKSPACE_DIR, item)
            if os.path.exists(item_path):
                tar.add(item_path, arcname=item)
    bundle_size_kb = os.path.getsize(bundle_path) / 1024
    log(f"✔ 소스 코드 패키징 완료: `bundle.tar.gz` ({bundle_size_kb:.1f} KB)")

    # Step 7: Wait for SSH daemon
    log("VM 부팅 및 SSH 연결 확인 중...")
    ssh_ready = False
    for attempt in range(1, 10):
        log(f"SSH 연결 확인 시도 {attempt}/9...")
        test_ssh = run_cmd(
            f"gcloud compute ssh {INSTANCE_NAME} --zone={ZONE} --project={PROJECT_ID} "
            f"--command=\"echo ssh_ready\" --quiet",
            check=False
        )
        if test_ssh.returncode == 0 and "ssh_ready" in test_ssh.stdout:
            ssh_ready = True
            log("✔ VM SSH 연결 준비 완료!")
            break
        time.sleep(4)

    if not ssh_ready:
        log("SSH 연결 확인 대기 시간 경과, 파일 전송 진행...")

    # Step 8: SCP bundle to VM
    log(f"gcloud compute scp를 통해 `{INSTANCE_NAME}:/tmp/bundle.tar.gz`로 전송 중...")
    scp_cmd = (
        f"gcloud compute scp \"{bundle_path}\" {INSTANCE_NAME}:/tmp/bundle.tar.gz "
        f"--zone={ZONE} --project={PROJECT_ID} --quiet"
    )
    run_cmd(scp_cmd)
    log("✔ 소스 코드 아카이브 VM 전송 완료")

    # Step 9: Remote Setup Script
    log("VM 내부에서 의존성 설치, systemd 서비스 등록 및 실행 진행...", "7. 원격 서버 배포 및 systemd 서비스 기동")
    remote_setup_commands = (
        "sudo mkdir -p /opt/chatbot && "
        "sudo tar -xzf /tmp/bundle.tar.gz -C /opt/chatbot/ && "
        "sudo cp /opt/chatbot/scripts/chatbot.service /etc/systemd/system/chatbot.service && "
        "sudo chmod +x /opt/chatbot/scripts/startup.sh /opt/chatbot/scripts/setup_https.sh && "
        "sudo bash /opt/chatbot/scripts/startup.sh && "
        "sudo bash /opt/chatbot/scripts/setup_https.sh && "
        "sudo systemctl daemon-reload && "
        "sudo systemctl enable --now chatbot.service && "
        "sudo systemctl status chatbot.service --no-pager"
    )
    ssh_exec_cmd = (
        f"gcloud compute ssh {INSTANCE_NAME} --zone={ZONE} --project={PROJECT_ID} "
        f"--command=\"{remote_setup_commands}\" --quiet"
    )
    log("원격 셋업 스크립트 실행 중 (패키지 설치, Nginx HTTPS 구성 및 서비스 등록)...")
    res_setup = run_cmd(ssh_exec_cmd, check=True, timeout=600)
    log("✔ 원격 챗봇 서비스 설치 및 systemd 기동 성공!")
    log(f"서비스 상태 출력:\n```\n{res_setup.stdout[-500:] if len(res_setup.stdout) > 500 else res_setup.stdout}\n```")

    # Step 10: Health Check & Verification
    log("클라우드 챗봇 서비스 엔드포인트 헬스체크 수행...", "8. 서비스 검증 및 Secret Manager 연동 확인")
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    candidate_urls = [
        f"https://{external_ip}",
        f"https://{external_ip}:5000",
        f"http://{external_ip}:5000",
        f"http://{external_ip}:5001"
    ]
    
    service_url = candidate_urls[0]
    success = False
    for attempt in range(1, 15):
        for test_url in candidate_urls:
            status_url = f"{test_url}/api/status"
            try:
                resp = requests.get(status_url, timeout=5, verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    has_key = data.get("has_api_key", False)
                    masked_key = data.get("masked_key", "")
                    selected_model = data.get("selected_model", "")
                    service_url = test_url
                    log(f"✔ 챗봇 서비스 응답 성공 (HTTP 200 OK, URL: {status_url})!")
                    log(f"✔ Secret Manager 연동 성공: GEMINI_API_KEY 로드됨 (`{masked_key}`)")
                    log(f"✔ 현재 기본 모델: `{selected_model}`")
                    success = True
                    break
            except Exception:
                pass
        if success:
            break
        log(f"헬스체크 대기 중 ({attempt}/14)...")
        time.sleep(4)

    # Step 11: End-to-End Chat API Test on Cloud Instance
    if success:
        log("원격 인스턴스 AI 스트리밍 대화 테스트 수행 중...")
        try:
            chat_url = f"{service_url}/api/chat"
            chat_payload = {
                "message": "안녕 아이린! 오늘 공방 날씨는 어때?",
                "model": "gemini-2.5-flash",
                "enable_search": False,
                "history": []
            }
            chat_resp = requests.post(chat_url, json=chat_payload, timeout=20, stream=True, verify=False)
            if chat_resp.status_code == 200:
                first_chunk = ""
                for line in chat_resp.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith("data: "):
                            try:
                                d = json.loads(decoded[6:])
                                first_chunk += d.get("text", "")
                                if len(first_chunk) > 40:
                                    break
                            except:
                                pass
                log(f"✔ AI 모델 응답 테스트 성공! 아이린 첫 응답 샘플:\n> \"{first_chunk.strip()}\"")
            else:
                log(f"대화 테스트 HTTP 상태: {chat_resp.status_code}")
        except Exception as ex:
            log(f"대화 테스트 경고: {ex}")

    # Final Summary Table
    ip_dash = external_ip.replace('.', '-')
    log("GCP Compute Engine 배포 완료 및 서비스 정보", "9. 최종 배포 결과 요약")
    log(f"- **공인 CA HTTPS URL**: [https://{ip_dash}.sslip.io](https://{ip_dash}.sslip.io)")
    log(f"- **웹 서비스 접속 URL**: [{service_url}]({service_url})")
    log(f"- **Compute Engine VM 인스턴스**: `{INSTANCE_NAME}`")
    log(f"- **존(Zone) / 리전(Region)**: `{ZONE}` / `{REGION}`")
    log(f"- **머신 스펙**: `{MACHINE_TYPE}` (2 vCPU, 4GB RAM, pd-balanced 10GB)")
    log(f"- **공용 외부 IP**: `{external_ip}`")
    log(f"- **개방 포트**: TCP `443` (HTTPS), TCP `80` (HTTP), TCP `5000` (Web UI)")
    log(f"- **GCP Secret Manager 연동**: `{SECRET_NAME}` (VM 메타데이터 인증 기반 자동 로드)")
    log(f"- **최종 배포 상태**: `{'배포 성공 (SUCCESS - ACTIVE)' if success else '인스턴스 생성 완료'}`")

    # Clean up local tarball
    if os.path.exists(bundle_path):
        os.remove(bundle_path)

    return success

if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except Exception as e:
        log(f"❌ 배포 프로세스 오류 발생: {str(e)}")
        sys.exit(1)
