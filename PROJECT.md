# 매일 동기부여

## 한 줄 정의

에디터가 큐레이션한 명언 라이브러리를 바탕으로, 사람이 자신의 상태와 상황에 맞는 문장을 다시 만나고 실제 도움을 받을 수 있게 하는 제품.

> "큐레이션된 문장 + 개인화 로직"이 핵심인 지혜 도구.

## 문제 정의

기존 명언/모티베이션 앱은 많은 문장을 보여주고 반복 노출하는 데 강하지만, 사용자의 현재 상태/상황/삶의 맥락에 깊게 맞춰주지 못한다. "잠깐 보고 지나가는 컨텐츠"에 머무른다.

이 프로젝트는 두 가지를 한 시스템 안에서 다룬다:

1. 좋은 문장을 모으는 일
2. 그 문장을 **언제, 어떤 사람에게, 어떤 방식으로 다시 꺼내줄 것인가**

## 핵심 전략

### 데이터가 자산이다

앱의 형태나 방향은 바뀔 수 있다. 하지만 잘 구조화된 명언 데이터는 어떤 방향으로든 활용 가능하다. 따라서 **퀄리티 높은 데이터를 모으고 관리하는 것이 최우선**이다.

### 데이터 레이어 구조

| 레이어 | 저장 내용 | 생성 주체 | 특성 |
|---|---|---|---|
| Layer 1: 원본 | 원문, 저자, 출처 등 불변 사실 | 에디터 | 절대 안 바뀜 |
| Layer 2: 메타데이터 | 저자 정보, 키워드, 상황 등 구조화된 속성 | 에디터 (or LLM+검수) | 거의 안 바뀜 |
| Layer 3: 임베딩 | 텍스트 벡터 | 자동 생성 | 모델 교체 시 재생성 |

- Layer 2는 "카테고리 분류"가 아니라 **사실 기반 속성의 기록**이다.
- 카테고리는 속성 조합으로 나중에 자유롭게 만든다. (예: "과학자 명언" = 저자_분야가 과학인 것)

### 데이터 스키마

**명언 테이블 (quotes)**

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | string | O | 고유 식별자 |
| `text` | string | O | 한국어 텍스트 |
| `text_original` | string | | 원문 (번역인 경우) |
| `original_language` | string | | 원어 코드 (en, de 등) |
| `author_id` | string | O | 저자 참조 |
| `source` | string | | 출처 (책, 연설, 인터뷰 등) |
| `year` | number | | 발언/출판 연도 |
| `keywords` | string[] | O | 키워드 목록 |
| `situation` | string[] | O | 어울리는 상황 목록 |

**저자 테이블 (authors)**

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | string | O | 고유 식별자 |
| `name` | string | O | 이름 |
| `profession` | string | O | 직업 |
| `field` | string | O | 분야 |
| `nationality` | char(2) | O | ISO 3166-1 alpha-2 국가코드 (예: KR, US, GB) |
| `birth_year` | number | O | 출생연도 |

**저자 관계 테이블 (author_relations)**

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | string | O | 고유 식별자 |
| `from_author_id` | string | O | 관계의 주체 |
| `to_author_id` | string | O | 관계의 대상 |
| `relation_type` | string | O | mentor / influenced_by / contemporary |

> `keywords`와 `situation`의 선택지 목록은 사전에 확정하지 않고, 데이터를 수집하면서 귀납적으로 수렴시킨다.

### 활용 시나리오 (예시)

같은 데이터로 다양한 방향이 가능하다:

- 직업별 명언 큐레이션
- 운동 종류별 명언
- 과학자 명언 모음
- 개인 상태/상황 기반 추천
- 일일 명언 위젯

## 제품 비전

### 코어

- 잘 선별된 명언 코어 데이터셋 (에디터 큐레이션 중심)
- 각 문장에 다양한 활용이 가능한 구조화된 메타데이터 부착
- 사용자가 상태/상황/목표를 표현하면, 맞는 문장 + 질문 + 행동 제안을 받음

### 사용자 입력의 역할

사용자가 직접 명언을 입력하는 기능은 **보조 기능**이다. 서비스의 주된 컨텐츠는 사전에 큐레이션된 문장들이다.

사용자가 제공하는 데이터:

- 현재 감정 / 상황 / 목표
- 추천 결과에 대한 반응 (좋았음 / 안 맞음)
- 짧은 메모 (이 문장이 나에게 어떻게 느껴졌는지)

## 제품 철학

- "많은 문장"보다 **"지금 나에게 맞는 한 문장"**이 중요하다.
- 기술은 푸시 알림으로 자극하기보다, **조용히 필요한 순간에 맞는 문장을 다시 연결해 주는 조력자**가 된다.

## 기술 스택

- **DB**: PostgreSQL (로컬, pg_trgm 확장 — 유사도 검색)
- **스크립트**: Python
- **LLM**: Claude API (수집용)
- **트렌드 분석**: pytrends (Google Trends)

## 프로젝트 구조

```
매일 동기부여/
├── PROJECT.md
├── requirements.txt
├── .env.example
├── .gitignore
├── db/
│   └── schema.sql              # PostgreSQL 전체 스키마
├── scripts/
│   ├── collect.py              # Claude API 명언 수집 (마스터 참조)
│   ├── validate.py             # 데이터 품질 검증
│   ├── factcheck.py            # 명언 팩트체크 (Claude API)
│   ├── trends.py               # Google Trends 분석
│   └── dashboard.py            # Flask 대시보드 (port 5050)
└── data/
    └── trends/                 # 트렌드 분석 결과 (JSON)
```

## 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY, PostgreSQL 접속 정보 입력

# 3. DB 생성
psql -U youheaukjun -f db/schema.sql

# 4. 트렌드 분석
python scripts/trends.py

# 5. 명언 수집 (마스터 목록 참조, 수집 이력 자동 기록)
python scripts/collect.py                    # 전체 카테고리
python scripts/collect.py --category 인생/삶  # 특정 카테고리만
python scripts/collect.py --dry-run           # DB 저장 없이 확인

# 6. 데이터 검증
python scripts/validate.py

# 7. 팩트체크
python scripts/factcheck.py                  # 미검증 전체
python scripts/factcheck.py --limit 10       # 10개만

# 8. 대시보드
python scripts/dashboard.py                  # http://localhost:5050
```

## 트렌드 분석 결과 (2026-04-12 기준)

### 글로벌

| 키워드 | 관심도 |
|---|---|
| love quotes | 67.1 |
| life quotes | 61.3 |
| funny quotes | 42.2 |
| motivational quotes | 35.2 |
| inspirational quotes | 23.5 |
| good morning quotes | 20.0 |
| study quotes | 13.5 |
| success quotes | 8.1 |

### 한국

| 키워드 | 관심도 |
|---|---|
| 명언 | 76.0 |
| 고사성어 | 52.0 |
| 공부명언 | 14.2 |
| 드라마명대사 | 5.1 |
| 인생명언 | 1.6 |

### 초기 수집 계획 (100개)

| 카테고리 | 배분 | 근거 |
|---|---|---|
| 인생/삶 | 25개 | 글로벌 2위, 가장 범용적 |
| 사랑/관계 | 15개 | 글로벌 1위 |
| 동기부여/성공 | 15개 | 꾸준한 수요 |
| 유머/위트 | 10개 | 글로벌 3위, 차별화 |
| 공부/학습 | 10개 | 한국 시장 특화 |
| 고사성어 | 15개 | 한국 시장 2위 |
| 과학/철학 | 10개 | 지적 깊이 확보 |

## 현재 단계

**데이터 수집 체계화 완료.** 마스터 테이블 기반 수집, 검증, 팩트체크, 수집 이력 관리 구축.

- 수집된 명언: 96개 / 저자: 72명 / 저자 관계: 59건
- 마스터: 키워드 44개, 상황 36개, 직업 20개, 분야 11개
