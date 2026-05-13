@echo off
echo ============================
echo  EXE 빌드 시작
echo ============================

pip install pyinstaller
pip install -r requirements.txt

echo.
echo --------------------------------------------
echo  PyInstaller Spec 파일을 사용하여 빌드합니다...
echo --------------------------------------------
pyinstaller --clean "타겟키워드분석.spec"

echo.
echo ============================
echo  빌드 완료: dist\타겟키워드분석.exe
echo ============================
pause
