# 새 프로젝트 환경 구축 가이드 — GitHub + Azure

> Supabase 이관이 아니라, **처음부터** GitHub + Azure로 새 프로젝트를 시작할 때 참고하는 문서.
> 기존 서비스 이관 작업은 [azure-migration-playbook.md](azure-migration-playbook.md) 참고.

---

## 0단계. 이 프로젝트가 정말 Azure 인프라가 필요한지 먼저 판단

**모든 프로젝트를 무조건 Azure로 만들 필요는 없다.** 아래 기준으로 먼저 판단할 것:

| 프로젝트 성격 | 추천 |
|---|---|
| 백엔드/DB 없이 단순 정적 페이지 | GitHub Pages, Vercel, Azure Static Web Apps 중 아무거나 (Azure 고집 불필요) |
| 프론트엔드 + 가벼운 API/DB 필요 | Azure Static Web Apps + Azure Functions + Azure PostgreSQL |
| 안 쓸 때 비용을 0에 가깝게 만들고 싶은 저트래픽 프로젝트 | Azure SQL 서버리스 티어 검토 (자동 일시정지 지원, PostgreSQL Flexible Server엔 없는 기능) |
| 이미지/AI 임베딩 검색 등 확장 기능 필요 | PostgreSQL (pgvector 등 확장 생태계가 훨씬 풍부) |
| 여러 소규모 프로젝트를 동시에 운영 중 | PostgreSQL 서버 하나에 데이터베이스를 여러 개 만들어 프로젝트별로 나눠 쓰기 (Azure는 프로젝트당 과금 아님 — Supabase와의 핵심 차이) |

---

## 1단계. GitHub 설정

### 저장소 생성

```bash
gh repo create <계정명>/<프로젝트명> --private --source=. --push
```

### ⚠️ 계정 확인부터 (자주 겪는 실수)

Windows에 여러 GitHub 계정이 캐시되어 있으면 `git push`가 엉뚱한 계정으로 시도되어 `403 Permission denied`가 난다. 프로젝트 시작 전에 미리 확인:

```cmd
git config user.name
git config user.email
gh auth status
```

캐시가 꼬여있으면: **자격 증명 관리자**(Windows 시작 메뉴 검색) → Windows 자격 증명 탭 → `git:https://github.com` 항목 제거 → 다음 `git push` 시 브라우저에서 올바른 계정 선택.

### .gitignore 필수 항목

```gitignore
# 환경/시크릿
.env
config.json
*.local.json

# Azure Functions 로컬 시크릿
**/local.settings.json

# Python
__pycache__/
venv/
.venv/

# 빌드 산출물
dist/
build/
```

**절대 원칙**: DB 연결 문자열, API 키, Function Key 등은 코드에 하드코딩하지 말고 항상 gitignore된 설정 파일이나 환경변수로.

---

## 2단계. Azure 계정/구독 확인

```cmd
az login
az account show
```

- 구독이 여러 개면 이 프로젝트에 쓸 구독을 명확히 확인 (`az account set --subscription <ID>`)
- 신규 계정이면 크레딧 만료일 확인 (`az account show`의 결과 또는 Azure Portal 홈 화면 "비용" 카드)

### 로컬 도구 vs 브라우저 Cloud Shell

| | 로컬 CLI | Azure Cloud Shell |
|---|---|---|
| 설치 | `winget install Microsoft.AzureCLI` 필요 | 불필요 (portal.azure.com 우측 상단 `>_` 아이콘) |
| 로그인 | `az login` 별도 필요 | 이미 로그인된 브라우저 세션 재사용, 로그인 절차 없음 |
| 언제 유리한가 | 반복 작업이 많고 로컬 스크립트와 연계할 때 | 처음 한두 번 빠르게 리소스만 만들 때, 설치 자체를 피하고 싶을 때 |

둘 다 같은 `az` 명령어를 쓰므로 아래 명령어들은 어느 쪽에서 실행해도 동일하다.

---

## 3단계. 프로젝트별 리소스 네이밍 규칙

Azure 리소스 이름은 종류마다 규칙이 다르고 **전역에서 유일**해야 하는 것들이 많다:

| 리소스 | 이름 규칙 | 예시 |
|---|---|---|
| Resource Group | 프로젝트 내에서만 유일하면 됨 | `rg-<프로젝트명>` |
| PostgreSQL 서버 | 전역 유일, 소문자/숫자/하이픈 | `<프로젝트명>-pg-<임의숫자>` |
| Storage 계정 | 전역 유일, **소문자+숫자만 (하이픈 불가)**, 3~24자 | `<프로젝트명>storage<임의숫자>` |
| Function App | 전역 유일 (URL의 일부가 됨) | `<프로젝트명>-func-<임의숫자>` |

이름 충돌 시 임의숫자 부분만 바꿔서 재시도하면 된다. 매번 새로 고민하지 말고 이 패턴을 그대로 재사용할 것.

---

## 4단계. 기본 리소스 생성 템플릿

```bash
# Resource Group
az group create --name rg-<프로젝트명> --location koreacentral

# DB (PostgreSQL 기준 — Azure SQL 서버리스로 갈 경우 별도 명령 필요)
az postgres flexible-server create \
  --resource-group rg-<프로젝트명> --name <프로젝트명>-pg-<번호> \
  --location koreacentral --admin-user <admin> --admin-password "<비밀번호>" \
  --sku-name Standard_B1ms --tier Burstable --version 16 --storage-size 32 \
  --public-access 0.0.0.0

# 내 PC 방화벽 허용 (IP는 반드시 cmd에서 curl ifconfig.me로 확인 — 브라우저 X, VPN/프록시로 다르게 나올 수 있음)
az postgres flexible-server firewall-rule create \
  --resource-group rg-<프로젝트명> --server-name <서버명> \
  --name AllowMyPC --start-ip-address <내IP> --end-ip-address <내IP>

az postgres flexible-server db create \
  --resource-group rg-<프로젝트명> --server-name <서버명> --name <DB명>

# Function App용 Storage + Function App
az storage account create --name <프로젝트명>storage<번호> --resource-group rg-<프로젝트명> --location koreacentral --sku Standard_LRS

az functionapp create \
  --resource-group rg-<프로젝트명> --consumption-plan-location koreacentral \
  --runtime python --runtime-version 3.11 --functions-version 4 \
  --name <프로젝트명>-func-<번호> --storage-account <프로젝트명>storage<번호> --os-type Linux
```

---

## 5단계. 로컬 데이터 확인 도구

Azure Portal은 **PostgreSQL 테이블 데이터를 직접 조회하는 화면이 없다** (Azure SQL은 있지만 PostgreSQL Flexible Server는 없음). 프로젝트 시작 시 **pgAdmin**을 같이 설치해서 서버를 등록해둘 것:

```cmd
winget install PostgreSQL.pgAdmin
```

pgAdmin 서버 등록 시 "Name" 필드는 표시용 별명일 뿐 실제 접속과 무관 — 프로젝트 이름 등 알아보기 쉬운 걸로.

---

## 6단계. API 인증 패턴 (매 프로젝트 재사용)

Azure Functions는 `authLevel: FUNCTION`으로 만들고, 클라이언트는 `x-functions-key` 헤더로 인증하는 패턴을 기본으로 쓴다:

```bash
az functionapp keys list --resource-group rg-<프로젝트명> --name <함수앱명>
```

`functionKeys.default` 값을 클라이언트 설정 파일에 저장하고 `x-functions-key` 헤더에 실어 호출.

DB 연결 문자열은 Function App의 App Settings(환경변수)에 저장:

```bash
az functionapp config appsettings set \
  --resource-group rg-<프로젝트명> --name <함수앱명> \
  --settings PG_CONN="postgresql://<user>:<pw>@<서버명>.postgres.database.azure.com:5432/<DB명>"
```

---

## 7단계. 배포 워크플로

```bash
cd <functions 코드 폴더>
func azure functionapp publish <함수앱명> --python
```

`local.settings.json`이 없으면 `--python` 등 언어를 명시적으로 지정해야 에러가 안 난다.

---

## 체크리스트 요약 (새 프로젝트 시작 시 순서대로)

- [ ] 0단계 판단: 이 프로젝트에 정말 Azure 백엔드가 필요한가?
- [ ] GitHub 저장소 생성 + 계정 확인 + `.gitignore` 설정
- [ ] `az login` + 구독 확인
- [ ] 리소스 네이밍 규칙에 맞춰 이름 정하기
- [ ] Resource Group → DB → 방화벽(내 IP는 cmd로 확인) → Storage → Function App 순서로 생성
- [ ] pgAdmin 설치 및 서버 등록
- [ ] Function Key 발급 + curl 테스트
- [ ] DB 연결 문자열은 App Settings로, 코드에 하드코딩 금지
- [ ] 클라이언트 코드에 API 엔드포인트 + 키 설정 반영
