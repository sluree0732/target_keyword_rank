# CLAUDE.md — 프로젝트 필수 규칙

## 코드 변경 후 필수 실행 순서 (CRITICAL)

코드 추가·수정·구현이 발생할 때마다 아래 3단계를 **반드시 한 번에** 완료한다.

### Step 1 — GitHub 커밋 & 푸시
```bash
git add <변경된 파일들>
git commit -m "type: 설명"   # feat / fix / chore / refactor 등
git push origin main
```

### Step 2 — EXE 재빌드
```bash
pyinstaller 타겟키워드분석.spec --noconfirm
```

### Step 3 — 완료 확인
- `dist/` 디렉토리에 EXE 생성 여부 확인
- GitHub에 커밋이 반영됐는지 확인

> **예외 없음.** 코드가 한 줄이라도 바뀌면 위 3단계를 모두 실행한다.

---

## 프로젝트 정보

- **저장소**: https://github.com/sluree0732/target_keyword_rank.git
- **브랜치**: main
- **spec 파일**: `타겟키워드분석.spec` (프로젝트 루트)
- **빌드 결과물**: `dist/` 디렉토리
