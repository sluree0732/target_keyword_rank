@echo off
echo ============================
echo  EXE 빌드 시작
echo ============================

pip install pyinstaller
pip install -r requirements.txt

pyinstaller ^
  --onedir ^
  --windowed ^
  --name "타겟키워드분석" ^
  --add-data "ui;ui" ^
  --add-data "core;core" ^
  --add-data "utils;utils" ^
  --hidden-import "curl_cffi" ^
  --hidden-import "kiwipiepy" ^
  --hidden-import "openpyxl" ^
  --collect-all "kiwipiepy" ^
  --collect-all "curl_cffi" ^
  main.py

echo.
echo ============================
echo  빌드 완료: dist\타겟키워드분석\
echo  타겟키워드분석.exe 를 실행하세요
echo ============================
pause
