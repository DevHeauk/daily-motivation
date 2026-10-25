# 매일 동기부여 MVP PRD (Product Requirements Document)

> 작성자: 김큐레이터 (PM) | 작성일: 2026-04-18 | 버전: 1.0

---

## 1. 제품 비전

**"지금 내 상황에 딱 맞는 명언을 만나는 가장 빠른 방법."**

명언 콘텐츠는 넘쳐나지만, 자신의 감정과 상황에 맞는 명언을 찾기는 어렵다. 매일 동기부여는 1,200개 이상의 검증된 명언 DB와 상황 기반 개인화 추천을 결합하여, 사용자가 앱을 열자마자 "지금 나에게 필요한 한 마디"를 제공한다.

---

## 2. 타겟 사용자

### 페르소나 A: 취준생 민지 (25세)

- 매일 아침 동기부여가 필요하고, 자소서에 인용할 명언을 찾는다.
- 사용 상황: "면접 전 긴장될 때", "자소서 쓰다 막힐 때", "탈락 통보 받았을 때"
- 기대: 상황을 고르면 바로 맞는 명언이 나오고, 저장해뒀다가 필요할 때 꺼내 볼 수 있다.

### 페르소나 B: 직장인 재현 (32세)

- 출퇴근길에 짧은 영감을 얻고 싶고, 좋은 문구를 SNS에 공유한다.
- 사용 상황: "월요일 아침 출근길", "야근하며 지칠 때", "팀장과 갈등 후"
- 기대: 매일 다른 명언을 추천받고, 취향에 맞는 명언이 점점 더 잘 나온다.

---

## 3. 핵심 유저 스토리

```
[첫 실행] 앱 설치 → 온보딩 (3단계)
  1단계: "지금 어떤 상황인가요?" (상황 2~3개 선택)
  2단계: "어떤 주제에 관심 있나요?" (키워드 그룹 2~3개 선택)
  3단계: 명언 3개를 보여주며 "마음에 드는 걸 골라보세요" (콜드스타트 해소)

[매일 사용] 앱 실행
  → 홈 화면에 "나를 위한 오늘의 명언" 표시 (개인화)
  → 마음에 들면 ♥ 좋아요, ↗ 공유
  → 더 보고 싶으면 "비슷한 명언 더보기" 또는 탐색 탭

[탐색] 특정 필요가 있을 때
  → 상황 탭에서 "포기하고 싶을 때" 선택
  → 해당 상황에 태깅된 명언 리스트 스크롤
  → 좋은 명언 발견 → 좋아요 → 나중에 좋아요 탭에서 다시 열람

[가치 인식 순간]
  → "이 앱은 내 상황을 알고 명언을 추천해주는구나"
  → 좋아요한 명언이 쌓이면서 나만의 명언 컬렉션이 형성
```

---

## 4. MVP 기능 스코프

### 4-A. 이미 구현된 기능 (재사용 가능)

| 기능 | 구현 위치 | 상태 | 비고 |
|------|----------|------|------|
| 오늘의 명언 | `HomeScreen.tsx` + `/app/api/v1/daily` | 완료 | 랜덤 x impact_score 가중치 기반. 개인화 아님 |
| 탐색 (카테고리/상황/저자) | `ExploreScreen.tsx` + API 3개 | 완료 | 키워드 그룹, 상황 그룹, 저자 목록 탭 전환 |
| 명언 리스트 (필터링 + 페이지네이션) | `QuoteListScreen.tsx` + `/app/api/v1/quotes` | 완료 | keyword_group, situation_group, author_id 필터 지원 |
| 명언 상세 | `QuoteDetailScreen.tsx` + `/app/api/v1/quotes/:id` | 완료 | 원문, 저자 정보, 출처, 키워드, 상황, 같은 저자 명언 표시 |
| 좋아요 (로컬 저장) | `FavoritesScreen.tsx` + `useFavorites` hook | 완료 | AsyncStorage 기반, 서버 동기화 없음 |
| 공유 | HomeScreen, QuoteDetailScreen | 완료 | `Share.share()` 텍스트 공유 |
| 하단 탭 네비게이션 | `RootNavigator.tsx` | 완료 | 홈, 탐색, 좋아요 3탭 |
| 다크 모드 UI | `colors.ts` | 완료 | 다크 테마 단일 모드 |
| 백엔드 API | `dashboard.py` | 완료 | Flask + PostgreSQL, 앱 전용 엔드포인트 7개 |
| DB (1,245개 명언) | `schema.sql` | 완료 | 저자, 키워드, 상황, 직업, 분야 마스터 테이블 완비 |

### 4-B. 새로 만들어야 할 기능

| # | 기능 | 설명 | 작업 범위 |
|---|------|------|----------|
| N1 | 온보딩 플로우 | 상황/키워드 선호도 수집 (3단계) | 프론트엔드 신규 화면 3개 + 로컬 저장 |
| N2 | 개인화 추천 로직 | 선호 데이터 기반 오늘의 명언 변경 | 백엔드 API 수정 + 신규 엔드포인트 |
| N3 | 사용자 선호 저장 API | 온보딩/좋아요 데이터를 서버에 저장 | DB 테이블 + API 2개 |
| N4 | 검색 기능 | 명언 텍스트 + 저자명 검색 | 프론트 검색 UI + 백엔드 API 1개 |
| N5 | 푸시 알림 (오늘의 명언) | 매일 아침 개인화 명언 푸시 | React Native Push + 서버 스케줄러 |
| N6 | 앱 아이콘 / 스플래시 | 앱스토어 등록용 에셋 | 디자인 + 설정 |
| N7 | 앱스토어 메타데이터 | 스크린샷, 설명, 키워드 | 마케팅 에셋 |

---

## 5. 개인화 추천 기능 상세

### 5-1. 온보딩 플로우

**목표**: 콜드스타트 문제 해결. 3단계, 총 30초 이내 완료.

#### Step 1 - 상황 선택 (SituationPickerScreen)

```
"지금 어떤 상황에 있나요?"
(최소 1개, 최대 3개 선택)

[위기/고난]  [성장/도전]  [관계]
[자기성찰]  [일/학업]    [일상]
```

- 상황 그룹 6개를 카드 UI로 표시 (DB의 situations.group_name 활용)
- 선택 시 해당 그룹 내 세부 상황도 함께 저장

#### Step 2 - 키워드 관심사 선택 (KeywordPickerScreen)

```
"어떤 주제의 명언을 좋아하세요?"
(최소 1개, 최대 3개 선택)

[감정]    [가치관]    [행동/태도]
[관계]    [지성]      [인생]
[사회]    [자연/과학]  [유머/표현]
```

- 키워드 그룹 9개를 카드 UI로 표시 (DB의 keywords.group_name 활용)

#### Step 3 - 명언 취향 확인 (QuoteTasteScreen)

```
"마음에 드는 명언에 ♥를 눌러보세요"
(3개 중 1개 이상 선택)

[명언 카드 1] ♡
[명언 카드 2] ♡
[명언 카드 3] ♡

              [시작하기 →]
```

- Step 1~2에서 선택한 상황/키워드 기반으로 명언 3개를 서버에서 추천
- 좋아요한 명언은 즐겨찾기에 자동 추가
- "시작하기" 누르면 홈으로 이동

#### 온보딩 데이터 저장

```typescript
// 로컬 (AsyncStorage)
interface UserPreference {
  situation_groups: string[];       // ["위기/고난", "성장/도전"]
  keyword_groups: string[];         // ["가치관", "행동/태도"]
  onboarding_completed: boolean;
  created_at: string;
}

// 서버 (Phase 2에서 동기화)
// MVP에서는 로컬 저장만. 서버 동기화는 회원 기능 추가 시.
```

### 5-2. 추천 로직

#### Phase 1 (MVP) - 상황 기반 필터링 + 가중 랜덤

온보딩에서 수집한 선호도를 기반으로 오늘의 명언을 선택한다.

```
추천 점수 = base_score(impact_score)
           + situation_match_bonus (선호 상황 일치 시 +3)
           + keyword_match_bonus (선호 키워드 그룹 일치 시 +2)
           + recency_penalty (최근 7일 내 본 명언 제외)
           + random_factor (0~1 범위 노이즈)
```

**백엔드 API 변경 (`/app/api/v1/daily`)**:

현재:
```python
ORDER BY random() * COALESCE(q.impact_score, 3) LIMIT 1
```

변경:
```python
# 쿼리 파라미터로 선호도 수신
# GET /app/api/v1/daily?situations=위기/고난,성장/도전&keywords=가치관,행동/태도

# 선호 상황/키워드에 매칭되는 명언에 가중치 부여
ORDER BY (
    COALESCE(q.impact_score, 3)
    + CASE WHEN EXISTS (
        SELECT 1 FROM situations s
        WHERE s.id = ANY(q.situation_ids)
        AND s.group_name = ANY(%s)
      ) THEN 3 ELSE 0 END
    + CASE WHEN EXISTS (
        SELECT 1 FROM keywords k
        WHERE k.id = ANY(q.keyword_ids)
        AND k.group_name = ANY(%s)
      ) THEN 2 ELSE 0 END
) * random()
DESC LIMIT 1
```

**신규 API: `GET /app/api/v1/recommend`**:

선호도 기반으로 명언 N개를 추천한다. 온보딩 Step 3와 "비슷한 명언 더보기"에 사용.

```
GET /app/api/v1/recommend?situations=위기/고난&keywords=가치관&limit=3&exclude=id1,id2
```

#### Phase 2 (후속) - 행동 기반 개인화

- 좋아요/조회 이력을 분석하여 선호 키워드/상황 가중치를 동적으로 조정
- 협업 필터링: "나와 비슷한 사용자가 좋아한 명언"
- 이 단계에서 회원 가입 + 서버 사이드 선호도 저장 필요

### 5-3. 데이터 구조

#### 추가 필요 테이블 (Phase 2용, MVP에서는 미구현)

```sql
-- 사용자 (Phase 2)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    device_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 사용자 선호도 (Phase 2)
CREATE TABLE IF NOT EXISTS user_preferences (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    situation_groups TEXT[],
    keyword_groups TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 조회 이력 (Phase 2)
CREATE TABLE IF NOT EXISTS user_quote_views (
    user_id VARCHAR(36) REFERENCES users(id),
    quote_id VARCHAR(36) REFERENCES quotes(id),
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, quote_id, viewed_at)
);
```

#### MVP에서의 저장 방식

- 온보딩 선호도: AsyncStorage에 `@user_preference` 키로 저장
- 최근 본 명언 ID: AsyncStorage에 `@recent_viewed` 키로 저장 (최대 50개, FIFO)
- 좋아요: 기존 `@favorites` 유지

---

## 6. 기능 우선순위 (RICE)

새로 구현할 기능만 대상으로 RICE 스코어를 산정한다.

| 기능 | Reach | Impact | Confidence | Effort | RICE Score | 우선순위 |
|------|-------|--------|------------|--------|------------|---------|
| | (1~10) | (1~5) | (0.5~1.0) | (주) | | |
| **N1. 온보딩 플로우** | 10 | 4 | 0.9 | 1 | **36.0** | **P0** |
| **N2. 개인화 추천 로직** | 10 | 5 | 0.8 | 1.5 | **26.7** | **P0** |
| **N4. 검색 기능** | 8 | 3 | 1.0 | 0.5 | **48.0** | **P0** |
| **N6. 앱 아이콘/스플래시** | 10 | 2 | 1.0 | 0.5 | **40.0** | **P0** |
| **N7. 앱스토어 메타데이터** | 10 | 2 | 1.0 | 0.5 | **40.0** | **P0** |
| **N3. 사용자 선호 저장 API** | 6 | 3 | 0.7 | 1 | **12.6** | **P1** |
| **N5. 푸시 알림** | 7 | 4 | 0.6 | 2 | **8.4** | **P2** |

### RICE 기준 설명

- **Reach**: 전체 사용자 중 해당 기능을 사용/경험할 비율 (10 = 100%)
- **Impact**: 사용자의 핵심 가치 인식에 미치는 영향 (5 = massive, 1 = minimal)
- **Confidence**: 예상대로 효과가 나올 확신도 (1.0 = 높음, 0.5 = 낮음)
- **Effort**: 개발 소요 주 (작을수록 점수 높음)
- **RICE Score**: Reach x Impact x Confidence / Effort

### MVP 릴리스 포함 범위

- **P0 (Must Have)**: N1, N2, N4, N6, N7 -- 앱스토어 출시 최소 요건
- **P1 (Should Have)**: N3 -- 출시 직후 1주 내 추가
- **P2 (Nice to Have)**: N5 -- 리텐션 데이터 확인 후 판단

---

## 7. MVP 제외 항목

| 제외 기능 | 제외 이유 |
|----------|----------|
| 회원 가입 / 로그인 | MVP에서는 로컬 저장만으로 충분. 회원 체계는 좋아요 동기화/소셜 기능 필요 시 도입 |
| 좋아요 서버 동기화 | 회원 기능 없이는 불가. 기기 변경 시 데이터 유실 감수 |
| 협업 필터링 추천 | 사용자 수 최소 1,000명 이상 필요. 초기에는 콘텐츠 기반 추천으로 충분 |
| 명언 제보 / UGC | 콘텐츠 검증 파이프라인 구축 전까지 위험. 가짜 명언 유입 우려 |
| 다국어 지원 | 한국 시장 PMF 검증 후 확장 |
| 라이트 모드 | 다크 모드 단일로 런칭. 사용자 피드백에 따라 추가 |
| 위젯 (iOS/Android) | 개발 비용 대비 MVP에서 우선순위 낮음. D7 리텐션 확인 후 도입 검토 |
| 알림 설정 커스터마이즈 | 푸시 알림 자체가 P2. 세부 설정은 더 후순위 |
| 저자 상세 페이지 | 현재 저자 관계(author_relations) 데이터 활용 가능하나, MVP 범위 초과 |
| 명언 컬렉션/폴더 | 좋아요 단일 리스트로 시작. 컬렉션 분류는 좋아요 30개 이상 사용자가 늘면 도입 |

---

## 8. 성공 지표 (KPI) -- 런칭 후 1개월 기준

### 핵심 지표 (North Star)

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| **D1 리텐션** | 40% 이상 | 설치 다음 날 앱 재실행 비율 |
| **D7 리텐션** | 20% 이상 | 설치 7일 후 재실행 비율 |
| **온보딩 완료율** | 70% 이상 | Step 3까지 완료한 사용자 / 앱 설치 사용자 |

### 참여 지표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 세션당 평균 명언 조회 수 | 3개 이상 | 상세 페이지 진입 횟수 / 세션 수 |
| 좋아요 비율 | DAU의 30% 이상이 1개 이상 좋아요 | 좋아요 이벤트 발생 유저 수 / DAU |
| 공유 비율 | DAU의 5% 이상 | 공유 이벤트 발생 유저 수 / DAU |
| 검색 사용률 | 주 1회 이상 사용자 20% | 검색 실행 유저 수 / WAU |

### 비즈니스 지표

| 지표 | 목표 | 비고 |
|------|------|------|
| 앱스토어 평점 | 4.5점 이상 | 리뷰 요청 타이밍: 좋아요 5회 이상 달성 시 |
| 다운로드 수 | 1,000건 (1개월) | ASO + 커뮤니티 바이럴 |
| 크래시 프리 비율 | 99.5% 이상 | Crashlytics 기준 |

### 개인화 효과 측정

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 온보딩 완료자 vs 미완료자 D7 리텐션 차이 | +10%p 이상 | A/B 비교 |
| 개인화 추천 명언 좋아요율 | 랜덤 대비 2배 이상 | 추천 명언 좋아요 / 추천 노출 vs 랜덤 좋아요 / 랜덤 노출 |

---

## 부록: 개발 로드맵

```
Week 1: N4(검색) + N6(아이콘/스플래시)
Week 2: N1(온보딩) + N2(개인화 추천 로직)
Week 3: N7(앱스토어 메타데이터) + QA + 버그 수정
Week 4: 앱스토어 심사 제출 + N3(선호 저장 API) 개발 시작
```
