# 매일 동기부여

사용자가 고른 주제의 명언을 매일 푸시로 보내고, 앱에서 모닥불 영상 위로 명언이 아래에서 위로 올라오며 보이는 앱.

이전 버전(명언 라이브러리 + 관리자 콘솔)은 git 태그 `legacy-v1`과 `~/Desktop/daily-motivation-backup/`에 보관되어 있다.

## 구조

- `server/app.py` — Flask 단일 파일. API + 매일 작업(`python app.py daily`)
- `app/` — Expo (React Native) 앱, iOS + Android

## 흐름

1. 앱은 첫 실행 때 기기 ID(UUID, `@device_id`)를 만든다. 주제 선택 시 푸시 토큰과 함께 `POST /devices` 등록
2. 명언은 주제별 풀(`quotes`)에 쌓인다. 풀에서 고를 게 없으면 OpenAI로 10개씩 새로 채운다
3. 매일 아침 cron이 `python app.py daily` 실행 → 주제별 오늘의 명언을 풀에서 골라 `daily_quotes`에 기록 → 해당 주제 기기에 Expo Push 발송
4. 앱은 `GET /quotes/today?topic=` 으로 오늘의 명언을 표시하고, 위로 스와이프하면 `POST /quotes/next` 로 이 기기가 본 적 없는 명언을 보여준다
5. 누구에게 어떤 명언을 보여줬는지는 `quote_views`에 기록한다 (source: push / today / swipe). 앱은 화면에 표시할 때 `POST /views`, 푸시는 발송 성공 시 서버가 기록

## 서버

```bash
cd server
pip install -r requirements.txt
cp .env.example .env    # DATABASE_URL, OPENAI_API_KEY
python app.py           # 개발 서버 localhost:5050
python app.py daily     # 오늘의 명언 생성 + 푸시
```

- 테이블은 서버 시작 시 `CREATE TABLE IF NOT EXISTS`로 생성 (`quotes`, `daily_quotes`, `devices`, `quote_views`)
- 주제 목록은 `TOPICS` 한 곳에서 관리. 앱은 `GET /topics`로 받아간다

## 앱

```bash
cd app
npm install
npx expo start
```

- 푸시는 Expo Go에서 동작하지 않는다 → development build 필요 (`npx eas-cli@latest build --profile development`)
- 서버 주소: `EXPO_PUBLIC_API_URL` 환경변수 (`app/.env`)
- 배경 영상 `assets/video/campfire.mp4`: Mixkit "Firewood burning in a campfire"(무료 라이선스)를 세로로 잘라 4초 루프로 만든 것

## 규칙

- 최대한 단순하게 유지한다. 화면/테이블/의존성 추가는 꼭 필요할 때만.
- DB는 psycopg2 + raw SQL, 사용자 입력은 `%s` 바인딩.
- 앱은 함수형 컴포넌트 + `StyleSheet.create()`. 네이티브 설정은 `app.json`에서만 (ios/android 폴더 직접 수정 금지).
