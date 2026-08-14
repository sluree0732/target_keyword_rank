# Azure 이관 플레이북 — GitHub + Render/Vercel + Supabase → Azure

> `target_keyword_rank` 프로젝트를 Supabase에서 Azure(PostgreSQL + Functions)로 이관하며 겪은 시행착오를 정리한 문서.
> 다른 프로젝트에서 같은 이관 작업을 할 때 이 파일을 프로젝트에 복사해 넣고 Claude Code에게 "이 문서 참고해서 Azure로 이관해줘"라고 요청하면 된다.

## 이 문서를 어떻게 쓰나

1. 이 파일을 이관하려는 프로젝트 폴더에 복사 (예: `docs/azure-migration-playbook.md`)
2. Claude Code에게 아래 요청 예시를 그대로(또는 상황에 맞게 수정해서) 전달
3. Claude Code가 먼저 해야 할 것: 아래 "0단계: 프로젝트 분석 체크리스트"부터 실행

### Claude Code에게 보낼 요청 예시 (복붙 가능)

```
이 프로젝트를 docs/azure-migration-playbook.md 참고해서 Azure로 이관하려고 해.

- 나는 Azure 사용 경험이 거의 없어서 각 단계를 상세하게 안내해줘
- 언제든 기존 서비스(Supabase 등)로 롤백 가능하도록 안전장치도 같이 만들어줘
- 먼저 문서의 0단계 체크리스트대로 이 프로젝트 코드를 분석해서
  (어떤 Supabase 기능을 쓰는지, 테이블 스키마, 이미지/파일 첨부 여부, 데이터량, 배포 방식)
  정리해서 알려줘. 실제 리소스 생성은 그다음에 진행하자.
```

**이렇게 요청하면 좋은 이유**:
- "0단계 체크리스트대로 코드 분석부터" → 컬럼 타입을 잘못 추측하는 등 이번에 겪은 실수를 미리 방지하는 핵심 단계라 반드시 먼저 시킬 것
- "Azure 경험 거의 없다" → 명령어 하나하나 상세히, 결과 확인하며 진행하는 방식으로 맞춰줌
- "롤백 안전장치도" → config 스위치, 필요하면 이중 쓰기(dual-write)까지 포함해서 계획을 짜줌

---

## 0단계. 프로젝트 분석 체크리스트 (이관 시작 전 필수 확인)

새 프로젝트마다 아래를 먼저 파악해야 계획이 정확해진다:

- [ ] Supabase에서 실제로 쓰는 기능이 뭔가? (REST 테이블 API만? Auth? Storage? Realtime?)
- [ ] 테이블 목록과 **실제 컬럼 타입** 확인 — Supabase 대시보드 → **Database → Schema Visualizer**에서 직접 확인할 것. 코드만 보고 타입을 추측하지 말 것 (예: 이번 프로젝트에서 `ids` 컬럼이 코드상 JSON처럼 다뤄져서 jsonb로 추측했으나 실제로는 `text[]`였음 — 잘못 추측하면 저장 시 데이터가 깨짐)
- [ ] 이미지/파일 첨부가 있는가? 있다면 **Supabase Storage**(별도 서비스, DB 덤프에 안 포함됨)인지 DB 컬럼에 직접 바이너리로 저장되는지 확인
- [ ] 데이터 양 (테이블당 대략 행 수, Storage 파일 용량)
- [ ] 현재 배포 방식 (데스크톱 EXE / 웹 서버 / Vercel·Render 정적+서버리스 등) — API 스위치 설계에 영향을 줌
- [ ] GitHub 저장소 소유 계정 확인 — push 권한 있는 계정인지 미리 확인 (아래 "자주 겪은 문제 → GitHub 계정 혼동" 참고)

---

## 1단계. 아키텍처 결정 (거의 항상 같은 답이 나옴)

| 결정 사항 | 기본 선택 | 이유 |
|---|---|---|
| DB 엔진 | **Azure Database for PostgreSQL** (Azure SQL 아님) | Supabase는 PostgreSQL 기반이라, 같은 엔진이어야 `pg_dump`/`pg_restore`로 스키마·데이터를 그대로 옮길 수 있음. Azure SQL로 가면 스키마 전면 재설계 필요 (배열 타입 자체가 없음 등) |
| API 레이어 | **Azure Functions** (Python) | Firebase Functions 등 서버리스 함수 경험이 있으면 학습 곡선이 가장 완만함. Data API builder(DAB)는 코드는 적지만 Container Apps 배포 + 자체 인증 체계를 새로 배워야 해서 오히려 진입장벽이 더 큼 |
| 파일 저장소 | Supabase Storage 썼다면 → **Azure Blob Storage** | DB와 완전히 별개 서비스. DB 마이그레이션과 별도 트랙으로 진행 |
| 인증 방식 | **Function Key** (`x-functions-key` 헤더) | Supabase의 `apikey` 헤더와 개념적으로 동일한 역할 |

**예외**: 여러 프로젝트를 운영 중이고 프로젝트별로 계속 인원/트래픽이 매우 적다면(안 쓸 때 비용 0으로 만들고 싶다면) Azure SQL 서버리스(자동 일시정지)가 유리할 수 있음 — 단, 이건 **처음부터 새로 만드는 프로젝트**에만 해당. Supabase에서 이관하는 경우는 항상 PostgreSQL.

---

## 2단계. 로컬 도구 준비

| 도구 | 용도 | 설치 |
|---|---|---|
| Azure CLI | 리소스 생성 명령 실행 | `winget install Microsoft.AzureCLI` (또는 브라우저의 **Azure Cloud Shell** 사용 — 설치/로그인 절차 자체가 생략됨, 이미 브라우저에 Azure 로그인돼 있으면 이쪽이 더 빠름) |
| Azure Functions Core Tools | 함수 로컬 테스트/배포 | `winget install Microsoft.Azure.FunctionsCoreTools` |
| pgAdmin | Postgres 데이터 확인/백업/복원 GUI | `winget install PostgreSQL.pgAdmin` |

**설치 후 cmd 창을 반드시 새로 열 것** (PATH 반영 안 되면 `az`, `func` 명령어 인식 안 됨).

`az login` 실행 → 브라우저 로그인 → **계정이 여러 개면 반드시 push 권한 있는 계정인지 확인**.

---

## 3단계. Azure 리소스 생성

```bash
# 1) Resource Group
az group create --name rg-<프로젝트명> --location koreacentral

# 2) PostgreSQL Flexible Server — --public-access 0.0.0.0 옵션이 Azure 서비스 접근 허용 방화벽 규칙을 자동 생성해줌 (별도 단계 불필요)
az postgres flexible-server create \
  --resource-group rg-<프로젝트명> \
  --name <서버명-고유해야함> \
  --location koreacentral \
  --admin-user <관리자ID> \
  --admin-password "<비밀번호>" \
  --sku-name Standard_B1ms --tier Burstable --version 16 --storage-size 32 \
  --public-access 0.0.0.0

# 3) 내 PC 접속용 방화벽 규칙 (아래 "IP 확인" 주의사항 참고)
az postgres flexible-server firewall-rule create \
  --resource-group rg-<프로젝트명> --server-name <서버명> \
  --name AllowMyPC --start-ip-address <내IP> --end-ip-address <내IP>

# 4) 데이터베이스 생성
az postgres flexible-server db create \
  --resource-group rg-<프로젝트명> --server-name <서버명> --name <DB명>
```

### ⚠️ CLI 옵션명 주의 (실제로 틀렸던 부분)

- `firewall-rule create`는 `--server-name`(서버 지정)과 `--name`(규칙 이름)이 **별개 옵션**. `--name`에 서버명을 넣으면 "the following arguments are required: --server-name" 에러
- `db create`는 `--database-name`이 아니라 **`--name`**

### ⚠️ 공인 IP는 반드시 cmd에서 확인 (브라우저 X)

```cmd
curl ifconfig.me
```

브라우저로 "my ip" 검색하면 브라우저 확장/프록시 설정 때문에 **실제와 다른 IP**가 나올 수 있음 (VPN 확장 프로그램 등). pgAdmin 같은 데스크톱 앱은 시스템 네트워크 경로를 타므로, **cmd에서 확인한 IP가 진짜**임.

---

## 4단계. 데이터 이관 (pgAdmin GUI 사용 권장)

CLI `pg_dump` 직접 타이핑보다 **pgAdmin의 백업/복원 GUI 기능**을 쓰는 게 명령어 실수가 없어서 안전함.

### 4-1. Supabase 연결 정보 확인

Supabase 대시보드 → 우측 상단 **Connect** 버튼 → **Direct Connection** 탭

### ⚠️ 반드시 "Session pooler" 사용 (Direct connection 아님)

> **Direct connection은 기본적으로 IPv6 전용**이라 일반 가정/사무실 네트워크(IPv4)에서 접속 자체가 안 될 수 있음. **Session pooler**를 선택할 것 — "Only recommended as an alternative to direct connection when connecting via an IPv4 network"라고 Supabase 화면에 직접 안내되어 있음.

Session pooler 연결 정보 형태:
```
postgresql://postgres.<project-ref>:[PASSWORD]@aws-x-xxxx.pooler.supabase.com:5432/postgres
```
- Username은 `postgres.<project-ref>` 전체를 그대로 사용 (project-ref 부분 생략하면 인증 실패)
- DB 비밀번호를 모르면 같은 화면의 **"Reset database password"**로 재발급 (REST API 키와는 별개 값)

### 4-2. pgAdmin에 Supabase 서버 등록

Servers 우클릭 → Register → Server. Connection 탭에 위 정보 입력 (Host/Port/Database/Username/Password).

### 4-3. 테이블별 백업

각 테이블 우클릭 → **Backup...** → Format: `Custom` → 파일 경로 지정 → Backup 클릭.

### 4-4. Azure DB에 복원

Azure 서버 트리에서 대상 DB 우클릭 → **Restore...** → 백업 파일 선택 → Restore 클릭.

### ⚠️ 복원 시 아래 에러들은 정상 — 무시해도 됨

```
ERROR: role "postgres" does not exist       (OWNER TO 구문)
ERROR: role "authenticated" does not exist  (CREATE POLICY 구문 — RLS 정책)
ERROR: role "anon" does not exist           (GRANT 구문)
```

Supabase 전용 역할(RLS 정책, 소유권, 익명/인증 사용자 권한)이 Azure엔 없어서 나는 에러. **테이블 구조와 실제 데이터는 정상적으로 복원됨** (로그에서 `creating TABLE`, `processing data for table`, `creating CONSTRAINT` 줄이 에러 없이 지나갔는지로 확인). `pg_restore: utility failed with exit code: 1`이 떠도 **exit code만으로 실패로 판단하지 말고 반드시 실제 데이터를 조회해서 확인**할 것:

```sql
SELECT * FROM <테이블명>;
```

### 4-5. RLS 비활성화 (안전장치)

복원 과정에서 RLS는 켜지는데 정책(POLICY)은 못 만들어져서, 소유자 외 접근이 막힐 수 있음. 이관한 테이블마다 실행:

```sql
ALTER TABLE <테이블명> DISABLE ROW LEVEL SECURITY;
```

---

## 5단계. Azure Functions 배포

```bash
# Storage 계정 (Function App 필수 의존성 — 앱 데이터 저장용이 아니라 Functions 자체 운영에 필요)
az storage account create --name <스토리지계정명-소문자숫자만> --resource-group rg-<프로젝트명> --location koreacentral --sku Standard_LRS

# Function App 생성 (Python, Consumption plan = 사용한 만큼만 과금)
az functionapp create \
  --resource-group rg-<프로젝트명> \
  --consumption-plan-location koreacentral \
  --runtime python --runtime-version 3.11 --functions-version 4 \
  --name <함수앱명-고유해야함> --storage-account <스토리지계정명> --os-type Linux

# DB 연결 문자열을 환경변수로 (코드에 하드코딩 금지)
az functionapp config appsettings set \
  --resource-group rg-<프로젝트명> --name <함수앱명> \
  --settings PG_CONN="postgresql://<user>:<pw>@<서버명>.postgres.database.azure.com:5432/<DB명>"
```

### 코드 구조 (Python v2 프로그래밍 모델)

- `function_app.py` — 엔트리포인트, Blueprint 등록
- 리소스별로 파일 분리 (예: `blog_lists_api.py`, `keyword_corrections_api.py`)
- `db.py` — `psycopg2` 연결 헬퍼, `os.environ['PG_CONN']`으로 환경변수 읽기
- `host.json`, `requirements.txt` (`azure-functions`, `psycopg2-binary`)
- `authLevel: FUNCTION` — Function Key 인증
- **컬럼 타입에 맞춰 코드 작성**: Postgres 배열(`text[]`) 컬럼에 값을 넣을 땐 `json.dumps()`로 문자열화하지 말고 **Python list를 그대로 psycopg2에 전달** (자동 변환됨). jsonb 컬럼이면 반대로 `json.dumps()` 필요 — 0단계에서 확인한 실제 컬럼 타입에 맞출 것

### 배포

```bash
cd <azure_functions 폴더>
func azure functionapp publish <함수앱명> --python
```

### ⚠️ 자주 나는 에러

- `Can't determine project language from files` → `local.settings.json`이 없어서 발생. `--python` 옵션을 명시적으로 붙이면 해결 (로컬 설정 파일 없이도 배포 가능)
- 로컬 Python 버전이 Function App 버전(예: 3.11)과 달라도 무관 — **원격 빌드(Remote build)**를 쓰기 때문에 실제 패키지 설치는 Azure 서버에서 이루어짐

### 배포 후 테스트

```bash
az functionapp keys list --resource-group rg-<프로젝트명> --name <함수앱명>
# functionKeys.default 값을 사용

curl -H "x-functions-key: <키>" https://<함수앱명>.azurewebsites.net/api/<엔드포인트>
```

---

## 6단계. 앱 코드에 백엔드 스위치 적용 (롤백 안전장치)

기존 코드 구조를 유지하면서, 설정 파일 값 하나로 Supabase ↔ Azure를 전환할 수 있게 만든다.

### 설계 원칙

- 기존 함수 시그니처(`get_all()`, `save()`, `delete()` 등)는 그대로 유지 → **호출부(UI 코드 등) 수정 불필요**
- 함수 내부에서 `config`의 `backend` 값(`"supabase"` | `"azure"`)에 따라 분기
- 민감 정보(연결 문자열, Function Key)는 `.gitignore` 처리된 설정 파일에만 저장, 코드에 하드코딩 금지

### 설정 파일 예시

```json
{
  "backend": "supabase",
  "azure": {
    "function_base_url": "https://<함수앱명>.azurewebsites.net/api",
    "function_key": "<Function Key>"
  }
}
```

### ⚠️ 패키징된 앱(EXE 등)이라면 — "즉시 전환"이 사실이 아닐 수 있음

PyInstaller 같은 도구로 실행 파일을 빌드하는 프로젝트라면, 설정 파일이 **빌드 시점에 실행 파일 안에 통째로 포함**되는 구조인지 먼저 확인할 것 (`.spec` 파일의 `datas` 항목 확인). 만약 그렇다면:
- `python main.py`(개발 모드 직접 실행): 설정 파일 수정 즉시 반영됨
- 배포된 실행 파일: 설정 파일을 수정해도 반영 안 됨 → **재빌드해야 전환됨**

"설정 값만 바꾸면 즉시 롤백"이라고 사용자에게 안내하기 전에 이 부분을 먼저 확인해서 정확히 전달할 것.

### (선택) 이중 쓰기(Dual-write) — 전환 과도기 안전장치

Azure로 전환했다가 다시 Supabase로 되돌릴 가능성이 있다면, 저장/삭제 시 **두 백엔드에 동시에 기록**하도록 만들어두면 어느 쪽으로 전환해도 데이터 유실이 없다.

```python
def save(...):
    if backend == 'azure':
        _save_azure(...)
        if dual_write:
            try_secondary(_save_supabase, ...)  # 실패해도 예외 전파 안 함, 로그만
    else:
        _save_supabase(...)
        if dual_write:
            try_secondary(_save_azure, ...)
```

조회는 여전히 `backend` 쪽 하나에서만 (양쪽 다 읽으면 복잡도만 커짐).

---

## 7단계. 검증

- [ ] pgAdmin으로 Azure DB의 행 수가 Supabase와 일치하는지 확인
- [ ] curl로 각 Function 엔드포인트 직접 호출해서 정상 응답 확인
- [ ] 실제 앱에서 `backend: azure`로 전체 흐름(생성/조회/수정/삭제) 테스트
- [ ] `backend: supabase`로 롤백 시 정상 동작 확인 (패키징 앱이면 재빌드 후 확인)
- [ ] Azure Portal → Function App → **Monitor/Log stream**에서 실제 호출이 찍히는지 확인 (문제 생겼을 때 원인 파악용)
- [ ] git 커밋 시 설정 파일(비밀번호/키 포함)이 `.gitignore`에 걸려 있는지 재확인

---

## 자주 겪은 문제 모음

| 증상 | 원인 | 해결 |
|---|---|---|
| `git push` 시 `Permission denied to <다른계정>` | Windows에 캐시된 GitHub 로그인이 저장소 소유 계정과 다름 | 자격 증명 관리자에서 `git:https://github.com` 항목 삭제 후 재로그인 시 올바른 계정 선택 |
| pgAdmin 접속 시 `password authentication failed` (여러 IP로 재시도 후 실패) | 비밀번호 오타 또는 예전 값 | Supabase 대시보드에서 "Reset database password"로 새로 발급받아 재시도 |
| pgAdmin에서 Session pooler 접속 안 됨 | Direct connection의 IPv6 문제와 혼동 | Session pooler는 IPv4 지원, 연결 문자열의 Username에 project-ref 포함 여부 재확인 |
| `pg_restore` exit code 1인데 데이터는 있음 | Supabase 전용 역할 GRANT/POLICY 구문 실패 (무해) | `SELECT count(*)`로 실제 데이터 존재 여부 직접 확인 |
| Function 배포 시 `Worker runtime cannot be 'None'` | `local.settings.json` 없음 | `func azure functionapp publish <이름> --python` 처럼 언어 명시 |
| 저장한 배열 데이터가 이상하게 들어감 | 컬럼이 실제로는 `text[]`인데 `jsonb`로 가정하고 `json.dumps()` 적용 | Supabase Schema Visualizer로 실제 타입 확인 후 코드 수정 |
