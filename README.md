
# 영양성분 계산기 Web MVP (FastAPI + SQLite)

## 1) 로컬 실행

### (1) 가상환경 설치
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### (2) 패키지 설치
```bash
pip install -r requirements.txt
```

### (3) 환경변수(.env)
`.env` 파일을 만들고 아래처럼 설정하세요.

```bash
ADMIN_PASSWORD=원하는관리자비번
SESSION_SECRET=랜덤문자열
DATABASE_URL=sqlite:///./data.db
EXCEL_PATH=./영양성분계산기_오터.xlsx
EXCEL_SHEET=원재료_DB
```

### (4) DB 초기 적재 (엑셀 → SQLite)
프로젝트 루트에 엑셀을 두고 실행:
```bash
python seed_from_excel.py
```

### (5) 서버 실행
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

접속:
- http://localhost:8000

관리자:
- http://localhost:8000/admin/ingredients (로그인 필요)

## 2) Render 배포

### Render 환경변수
- `ADMIN_PASSWORD`
- `SESSION_SECRET`
- `DATABASE_URL`  (Render Postgres 사용을 권장하지만 SQLite도 가능)
- (선택) `EXCEL_PATH`, `EXCEL_SHEET`

### Start Command
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

> 참고: Render의 파일시스템은 배포 방식에 따라 영구 저장이 제한될 수 있어요.
> 원재료 DB를 계속 운영/수정할 예정이면 Render Postgres를 연결하는 구성을 추천합니다.
