@echo off
chcp 65001 > nul
echo ===================================================
echo   Gemini AI Studio - 로컬 웹 챗봇 서비스 시작
echo ===================================================

:: Python 실행 경로 확인 (시스템 PATH 우선, 없으면 Anaconda 경로 사용)
where python >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=python
) else (
    if exist "C:\Users\think\anaconda3\python.exe" (
        set "PY_CMD=C:\Users\think\anaconda3\python.exe"
    ) else (
        echo [오류] Python 실행 파일을 찾을 수 없습니다.
        pause
        exit /b 1
    )
)

echo [정보] Python 사용: %PY_CMD%
echo [정보] 의존성 확인 중...
%PY_CMD% -m pip install -r requirements.txt --quiet

echo.
echo [정보] 로컬 서버를 실행합니다: http://localhost:5000
echo [정보] 종료하려면 이 창에서 Ctrl + C 를 누르세요.
echo.

:: 브라우저 자동 실행 (1초 후)
start "" cmd /c "timeout /t 2 /nobreak > nul && start http://localhost:5000"

:: Flask 서버 실행
%PY_CMD% app.py

pause
