# 매일 동기부여

큐레이션된 명언 라이브러리 + 개인화 추천을 목표로 하는 프로젝트.

## 기술 스택

- **언어**: Python
- **DB**: PostgreSQL (pg_trgm 확장 — 유사도 검색)
- **LLM**: Claude API (anthropic SDK) — 명언 수집용
- **웹**: Flask (대시보드)
- **기타**: pytrends (Google Trends 분석)

## 프로젝트 구조

- `db/schema.sql` — PostgreSQL 테이블 정의 (quotes, authors, author_relations)
- `scripts/collect.py` — Claude API로 명언 수집 + DB 저장 (메인 스크립트)
- `scripts/trends.py` — Google Trends 카테고리 관심도 분석
- `scripts/dashboard.py` — Flask 기반 데이터 현황 대시보드 (localhost:5050)
- `scripts/seed_*.py` — 초기 데이터 시딩 스크립트
- `insert_quotes.py` — 수동 명언 삽입 (고사성어, 과학/철학)
- `data/trends/` — 트렌드 분석 결과 JSON

## 실행 방법

```bash
pip install -r requirements.txt
cp .env.example .env              # API키, DB 접속 정보 설정

# DB 초기화
psql -U youheaukjun -f db/schema.sql

# 명언 수집
python scripts/collect.py                    # 전체 카테고리
python scripts/collect.py --category 인생/삶  # 특정 카테고리
python scripts/collect.py --dry-run           # DB 저장 없이 확인

# 대시보드
python scripts/dashboard.py
```

## 환경변수 (.env)

- `ANTHROPIC_API_KEY` — Claude API 키
- `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE` — PostgreSQL 접속 정보

## 기술 스택 상세

### 백엔드 (Python)
- **Flask** (dashboard.py 단일 파일) — 대시보드 + 앱 API + 관리자 API
- **psycopg2** — PostgreSQL 드라이버 (ORM 없음, raw SQL)
- **gunicorn** — 프로덕션 서버 (`Procfile`: `gunicorn scripts.dashboard:app`)
- **anthropic SDK** — Claude API (수집, 팩트체크)
- **배포**: Railway (내부 PostgreSQL + gunicorn)

### 모바일 앱 (TypeScript)
- **React Native 0.85** + React 19
- **React Navigation v7** (bottom tabs + native stack)
- **AsyncStorage** — 로컬 저장 (선호도, 좋아요, 행동 로그)
- **Vanilla fetch** — API 호출 (axios 등 미사용)
- 상태관리 라이브러리 없음 (useState/useRef로 충분)

### 데이터베이스
- **PostgreSQL** + pg_trgm (유사도 검색)
- PK: UUID (VARCHAR(36))
- 태깅: `keyword_ids VARCHAR(36)[]`, `situation_ids VARCHAR(36)[]` (배열)
- 레거시: `keywords JSONB`, `situation JSONB` (하위 호환용, 신규 코드에서 사용 금지)

## 코딩 규칙

### Python (백엔드)

1. **DB 패턴**: `get_db()` → `conn.cursor()` → execute → `cur.close(); conn.close()`. ORM 사용 금지.
2. **API 응답**: 항상 `jsonify()` 사용. 리스트 API는 `{"엔티티명": [...], "total": N, "page": N}` 형식 (예: `{"quotes": [...]}`).
3. **인증**: 관리자 API(`/admin/api/*`)는 `@require_admin` 데코레이터 필수. 환경변수 `ADMIN_TOKEN`.
4. **에러 응답**: `jsonify({"error": "메시지"})` + 적절한 HTTP 상태코드.
5. **SQL 안전**: 사용자 입력은 반드시 `%s` 파라미터 바인딩. f-string에 사용자 값 직접 삽입 금지.
6. **파일 구조**: 백엔드는 `scripts/dashboard.py` 단일 파일. 분리하지 않는다.

### TypeScript (앱)

1. **함수형 컴포넌트 only**: class 컴포넌트 사용 금지.
2. **네이밍**: 화면은 `XxxScreen.tsx`, 훅은 `useXxx.ts`, 저장소는 `storage/xxx.ts`.
3. **스타일**: `StyleSheet.create()` 사용. 인라인 스타일 최소화. 색상은 `colors.ts`에서 import.
4. **API**: `api/client.ts`의 `fetchJSON<T>()` 헬퍼 사용. 직접 fetch 호출 금지.
5. **로컬 저장**: AsyncStorage 사용. 키 prefix `@` (예: `@favorites`, `@device_id`).
6. **타입**: `types/index.ts`에 공유 타입 정의. any 사용 금지.
7. **아이콘**: `react-native-vector-icons/Ionicons` 사용. 이모지(emoji) 사용 금지.

### 공통

1. **ID**: 모든 테이블 PK는 UUID v4 (Python: `str(uuid.uuid4())`).
2. **날짜**: DB는 `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`, 앱은 `new Date().toISOString()`.
3. **환경변수**: `.env` + `python-dotenv`. 앱은 `constants/config.ts`.
4. **에러 처리**: 외부 호출(DB, API, 네트워크)만 try/catch. 내부 로직에 방어적 코딩 불필요.

## 배포

- **백엔드**: `git push origin master` → Railway 자동 배포 (또는 `railway up`)
- **DB 마이그레이션**: `POST /admin/migrate` 또는 Railway CLI (`railway run psql -c "..."`)
- **환경변수**: Railway 대시보드에서 설정 (`DATABASE_URL`, `ADMIN_TOKEN`, `ANTHROPIC_API_KEY`)
- **앱**: Android 릴리스 빌드 (`app/android/` 디렉토리)

## 주의사항

- 모든 스크립트는 psycopg2 (PostgreSQL) 사용
- keyword_ids/situation_ids 배열 사용. 레거시 JSONB(keywords, situation) 필드는 신규 코드에서 참조 금지
- 중복 검사: 정확 매칭 + trigram 유사도 (threshold 0.4)

## 명언 수집 규칙

### 데이터 검증

1. **실존 명언만 수집** — 절대 지어내지 않는다. 출처가 불확실하면 source를 null로 한다.
2. **저자 정보 검증** — name, profession, field, nationality, birth_year는 사실 기반이어야 한다. 추정값은 사용하지 않는다.
3. **원문 필수** — 번역 명언은 반드시 text_original과 original_language를 함께 제공한다. 한국어 원문이면 original_language를 "ko"로 한다.
4. **중복 방지** — DB 저장 전 반드시 중복 검사를 거친다 (정확 매칭 → trigram 유사도 0.4 이상이면 중복 판정).
5. **태깅 일관성** — keywords, situation은 DB의 마스터 테이블 목록에서 선택한다. 새 항목 추가 시 `_new:이름` 형식을 사용하고 로그에 기록한다.

### 저자 관계 (author_relations)

- 역사적으로 확인된 관계만 기록한다. 추측 금지.
- mentor: 직접적인 스승→제자
- influenced_by: 사상적 영향 (준 사람→받은 사람)
- contemporary: 같은 시대 교류 (양방향 저장)
- 관계가 없으면 빈 배열 []

### 상태 관리 (status)

- `draft` — AI 수집 직후 (기본값). 검증 전.
- `reviewed` — 사람이 내용 확인 완료.
- `published` — 서비스 노출 가능.
- `rejected` — 가짜 명언, 부정확 등으로 폐기.

### 출처 신뢰도 (source_reliability)

- `verified` — 원전 확인됨 (책, 연설문, 서신 등에서 직접 대조)
- `attributed` — 구체적 출처가 있으나 원전 대조는 안 됨
- `disputed` — 실제 발언자 논란 있음
- `unknown` — 출처 불명 (source가 null)

### 수집 이력 관리

1. **collection_logs 테이블** — 모든 수집은 카테고리별로 요청 수, 저장 수, 중복 수, 오류 수를 기록한다.
2. **collection_log_id** — 각 명언은 어떤 수집 배치에서 들어왔는지 추적 가능하다.
3. **dry-run 우선** — 새로운 카테고리나 대량 수집 전에 `--dry-run`으로 먼저 확인한다.
4. **카테고리별 수집** — 한 번에 전체를 수집하기보다 `--category`로 나눠서 진행하고, 각 결과를 확인한 뒤 다음으로 넘어간다.
5. **수동 삽입 시** — seed 스크립트로 수동 데이터를 넣을 때도 중복 검사를 반드시 수행한다.

### 수집 계획 (COLLECTION_PLAN)

| 카테고리 | 목표 | 비고 |
|---|---|---|
| 인생/삶 | 25개 | 가장 범용적 |
| 사랑/관계 | 15개 | 글로벌 1위 관심도 |
| 동기부여/성공 | 15개 | 꾸준한 수요 |
| 유머/위트 | 10개 | 차별화 |
| 공부/학습 | 10개 | 한국 시장 특화 |
| 고사성어 | 15개 | 한국 시장 2위 |
| 과학/철학 | 10개 | 지적 깊이 확보 |

### 데이터 품질 기준

- **다양성**: 시대, 국적, 분야, 성별이 편중되지 않도록 한다.
- **nationality**: 반드시 ISO 3166-1 alpha-2 코드 사용 (KR, US, GB, DE, CN 등). "한국", "미국" 같은 한글 국가명 사용 금지.
- **고사성어**: text에 한자 + 뜻풀이 포함, text_original에 한자만, original_language는 "zh".

### 그룹 체계 (마스터 테이블)

키워드, 상황, 직업은 `group_name`으로 분류한다. 시드 데이터: `db/seed_groups.sql`

**키워드 그룹**: 감정, 가치관, 행동/태도, 관계, 지성, 인생, 사회, 자연/과학, 유머/표현
**상황 그룹**: 위기/고난, 성장/도전, 관계, 자기성찰, 일/학업, 일상
**직업 그룹**: 사상/학문, 과학/기술, 문학/예술, 정치/군사, 경제/산업, 종교/정신, 대중문화
