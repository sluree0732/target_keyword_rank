@echo off
chcp 65001 >nul
echo Python 설치 확인 중...

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org 에서 Python을 설치한 후 다시 실행하세요.
    pause
    exit /b 1
)

echo 패키지 설치 확인 중...
pip install -r requirements.txt --quiet

echo 프로그램 실행 중...
python main.py
