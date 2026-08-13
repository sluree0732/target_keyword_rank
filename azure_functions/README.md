# Azure Functions — Supabase 대체 API

`blog_lists`, `keyword_corrections` 테이블에 대한 REST API. 기존 Supabase REST API(PostgREST)를 대체한다.
전체 마이그레이션 계획은 `C:\Users\SW-2\.claude\plans\velvety-skipping-rossum.md` 참고.

## 엔드포인트

| Method | Path | 대응 |
|---|---|---|
| GET | `/api/blog_lists` | `blog_list_store.get_all()` |
| POST | `/api/blog_lists` `{name, ids}` | `blog_list_store.save()` |
| DELETE | `/api/blog_lists?name=...` | `blog_list_store.delete()` |
| POST | `/api/keyword_corrections` `{post_title, grade, keyword}` | `keyword_corrections_store.save()` |
| POST | `/api/keyword_corrections/fetch` `{titles, grade}` | `keyword_corrections_store.fetch_exact_matches()` |

모든 요청에 `x-functions-key` 헤더 필요 (Function Key 인증).

## 로컬 개발

```bash
cd azure_functions
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy local.settings.json.example local.settings.json
# local.settings.json의 PG_CONN을 실제 Azure PostgreSQL 연결 문자열로 수정

func start
```

## 배포

```bash
az functionapp config appsettings set \
  --resource-group rg-target-keyword-rank --name <function-app-이름> \
  --settings PG_CONN="<Azure PostgreSQL 연결 문자열>"

func azure functionapp publish <function-app-이름>
```

## 사전 필요 DB 스키마

```sql
CREATE TABLE blog_lists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    ids JSONB NOT NULL
);

CREATE TABLE keyword_corrections (
    id SERIAL PRIMARY KEY,
    post_title TEXT NOT NULL,
    grade INTEGER NOT NULL,
    keyword TEXT NOT NULL
);
```

(계획서 Phase 2의 `pg_dump`/`psql`로 Supabase에서 그대로 이관하면 이 CREATE TABLE은 별도로 실행할 필요 없음 — 덤프에 스키마가 포함됨)
