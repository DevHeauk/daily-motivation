"""매일 동기부여 서버.

- Flask API: 주제 목록, 오늘의 명언, 기기 등록
- `python app.py daily`: 주제별 오늘의 명언 생성 + 푸시 발송 (매일 cron)
"""
import json
import os
import sys
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from openai import OpenAI

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
KST = ZoneInfo("Asia/Seoul")
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

TOPICS = ["인생", "사랑", "성공", "위로", "용기", "공부"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id VARCHAR(36) PRIMARY KEY,
    topic VARCHAR(20) NOT NULL,
    text TEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (topic, text)
);
CREATE TABLE IF NOT EXISTS daily_quotes (
    date DATE NOT NULL,
    topic VARCHAR(20) NOT NULL,
    quote_id VARCHAR(36) NOT NULL REFERENCES quotes (id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, topic)
);
CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(36) PRIMARY KEY,
    push_token VARCHAR(255) UNIQUE,
    topic VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 누구에게(device_id) 어떤 명언을(quote_id) 어떤 경로로(source) 보여줬는지
CREATE TABLE IF NOT EXISTS quote_views (
    id VARCHAR(36) PRIMARY KEY,
    device_id VARCHAR(36) NOT NULL,
    quote_id VARCHAR(36) NOT NULL REFERENCES quotes (id),
    source VARCHAR(10) NOT NULL,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS quote_views_device_idx ON quote_views (device_id);
"""

# push: 푸시 발송, today: 앱에서 오늘의 명언 표시, swipe: 스와이프로 표시
VIEW_SOURCES = ("push", "today", "swipe")

# 풀이 바닥나면 한 번에 만드는 명언 수
BATCH_SIZE = 10

QUOTES_FORMAT = {
    "type": "json_schema",
    "name": "quotes",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "quotes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "author": {"type": "string"},
                    },
                    "required": ["text", "author"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["quotes"],
        "additionalProperties": False,
    },
}

app = Flask(__name__)


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(SCHEMA)
    conn.commit()
    cur.close()
    conn.close()


def today():
    return datetime.now(KST).date()


def generate_quotes(topic, avoid):
    """OpenAI로 실존 명언 BATCH_SIZE개를 고른다. 이미 있는 명언은 피한다."""
    client = OpenAI()
    avoid_list = "\n".join(f"- {t}" for t in avoid) or "(없음)"
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=(
            f"당신은 명언 큐레이터입니다. 주어진 주제에 맞는 실존 명언 {BATCH_SIZE}개를 고릅니다. "
            "지어내지 말고, 실제 인물이 남긴 것으로 널리 알려진 명언만 고르세요. "
            "시대, 국적, 분야가 겹치지 않게 다양하게 고르세요. "
            "text는 자연스러운 한국어 문장(번역 포함), author는 한국어 표기 인물명입니다."
        ),
        input=f"주제: {topic}\n\n이미 있어서 제외할 명언:\n{avoid_list}",
        text={"format": QUOTES_FORMAT},
    )
    return json.loads(response.output_text)["quotes"]


def fill_pool(cur, topic):
    cur.execute(
        "SELECT text FROM quotes WHERE topic = %s ORDER BY created_at DESC LIMIT 150",
        (topic,),
    )
    avoid = [r[0] for r in cur.fetchall()]
    for q in generate_quotes(topic, avoid):
        cur.execute(
            "INSERT INTO quotes (id, topic, text, author) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (topic, text) DO NOTHING",
            (str(uuid.uuid4()), topic, q["text"], q["author"]),
        )


def pick_quote(cur, topic, exclude_ids):
    """exclude_ids를 뺀 주제 명언 중 하나를 무작위로 고른다. 없으면 풀을 채우고 다시 고른다."""
    sql = (
        "SELECT id, text, author FROM quotes "
        "WHERE topic = %s AND NOT (id = ANY(%s)) ORDER BY random() LIMIT 1"
    )
    cur.execute(sql, (topic, exclude_ids))
    row = cur.fetchone()
    if not row:
        fill_pool(cur, topic)
        cur.execute(sql, (topic, exclude_ids))
        row = cur.fetchone()
    return {"id": row[0], "topic": topic, "text": row[1], "author": row[2]} if row else None


def find_daily(cur, date, topic):
    cur.execute(
        "SELECT q.id, q.text, q.author FROM daily_quotes d JOIN quotes q ON q.id = d.quote_id "
        "WHERE d.date = %s AND d.topic = %s",
        (date, topic),
    )
    row = cur.fetchone()
    return {"id": row[0], "topic": topic, "text": row[1], "author": row[2]} if row else None


def get_or_create_daily(topic):
    date = today()
    conn = get_db()
    cur = conn.cursor()
    quote = find_daily(cur, date, topic)
    if not quote:
        # 이전에 오늘의 명언으로 쓴 적 없는 것 중에서 고른다
        cur.execute("SELECT quote_id FROM daily_quotes WHERE topic = %s", (topic,))
        used = [r[0] for r in cur.fetchall()]
        picked = pick_quote(cur, topic, used)
        cur.execute(
            "INSERT INTO daily_quotes (date, topic, quote_id) VALUES (%s, %s, %s) "
            "ON CONFLICT (date, topic) DO NOTHING",
            (date, topic, picked["id"]),
        )
        conn.commit()
        # 동시 요청으로 다른 쪽이 먼저 저장했다면 그 명언을 쓴다
        quote = find_daily(cur, date, topic)
    cur.close()
    conn.close()
    return {"date": date.isoformat(), **quote}


def next_quote(topic, device_id, seen):
    """이 기기가 본 적 없는 명언을 고른다. seen은 앱이 미리 받아 둔(아직 기록 전) 명언."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT quote_id FROM quote_views WHERE device_id = %s", (device_id,))
    viewed = [r[0] for r in cur.fetchall()]
    quote = pick_quote(cur, topic, viewed + seen)
    conn.commit()
    cur.close()
    conn.close()
    return quote


def send_push(topic, quote):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, push_token FROM devices WHERE topic = %s AND push_token IS NOT NULL",
        (topic,),
    )
    devices = cur.fetchall()

    sent, dead = [], []
    for i in range(0, len(devices), 100):
        chunk = devices[i : i + 100]
        messages = [
            {
                "to": token,
                "title": f"오늘의 {topic} 명언",
                "body": f"{quote['text']} — {quote['author']}",
                "sound": "default",
            }
            for _, token in chunk
        ]
        try:
            res = requests.post(EXPO_PUSH_URL, json=messages, timeout=30)
            res.raise_for_status()
        except requests.RequestException as e:
            print(f"[push] {topic} 발송 실패: {e}", flush=True)
            continue
        for (device_id, token), ticket in zip(chunk, res.json()["data"]):
            if ticket.get("status") == "ok":
                sent.append(device_id)
            elif ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                dead.append(token)

    for device_id in sent:
        cur.execute(
            "INSERT INTO quote_views (id, device_id, quote_id, source) VALUES (%s, %s, %s, 'push')",
            (str(uuid.uuid4()), device_id, quote["id"]),
        )
    if dead:
        cur.execute("UPDATE devices SET push_token = NULL WHERE push_token = ANY(%s)", (dead,))
    conn.commit()
    cur.close()
    conn.close()
    print(f"[push] {topic}: {len(sent)}/{len(devices)}대 발송, 만료 토큰 {len(dead)}개", flush=True)


def run_daily():
    for topic in TOPICS:
        try:
            quote = get_or_create_daily(topic)
        except Exception as e:
            print(f"[daily] {topic} 생성 실패: {e}", flush=True)
            continue
        print(f"[daily] {topic}: {quote['text']} — {quote['author']}", flush=True)
        send_push(topic, quote)


@app.get("/topics")
def topics():
    return jsonify({"topics": TOPICS})


@app.get("/quotes/today")
def quote_today():
    topic = request.args.get("topic")
    if topic not in TOPICS:
        return jsonify({"error": "알 수 없는 주제입니다"}), 400
    try:
        return jsonify(get_or_create_daily(topic))
    except Exception as e:
        print(f"[api] {topic} 명언 조회 실패: {e}", flush=True)
        return jsonify({"error": "명언을 불러오지 못했습니다"}), 502


@app.post("/quotes/next")
def quote_next():
    body = request.get_json(silent=True) or {}
    topic = body.get("topic")
    device_id = body.get("device_id")
    seen = body.get("seen") or []
    if topic not in TOPICS or not device_id or not isinstance(seen, list):
        return jsonify({"error": "topic, device_id, seen 목록이 필요합니다"}), 400
    try:
        quote = next_quote(topic, device_id, [str(s) for s in seen[-200:]])
    except Exception as e:
        print(f"[api] {topic} 다음 명언 조회 실패: {e}", flush=True)
        return jsonify({"error": "명언을 불러오지 못했습니다"}), 502
    if not quote:
        return jsonify({"error": "더 이상 새 명언이 없습니다"}), 404
    return jsonify(quote)


@app.post("/views")
def record_view():
    body = request.get_json(silent=True) or {}
    device_id = body.get("device_id")
    quote_id = body.get("quote_id")
    source = body.get("source")
    if not device_id or not quote_id or source not in VIEW_SOURCES:
        return jsonify({"error": "device_id, quote_id, 올바른 source가 필요합니다"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO quote_views (id, device_id, quote_id, source) "
        "SELECT %s, %s, id, %s FROM quotes WHERE id = %s",
        (str(uuid.uuid4()), device_id, source, quote_id),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


@app.post("/devices")
def register_device():
    body = request.get_json(silent=True) or {}
    device_id = body.get("device_id")
    topic = body.get("topic")
    token = body.get("token")
    if not device_id or len(device_id) > 36 or topic not in TOPICS:
        return jsonify({"error": "device_id와 올바른 topic이 필요합니다"}), 400
    conn = get_db()
    cur = conn.cursor()
    if token:
        # 앱 재설치 등으로 같은 토큰이 다른 기기 ID에 남아 있으면 떼어낸다
        cur.execute(
            "UPDATE devices SET push_token = NULL WHERE push_token = %s AND id <> %s",
            (token, device_id),
        )
    cur.execute(
        "INSERT INTO devices (id, push_token, topic) VALUES (%s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET topic = EXCLUDED.topic, "
        "push_token = COALESCE(EXCLUDED.push_token, devices.push_token), "
        "updated_at = CURRENT_TIMESTAMP",
        (device_id, token, topic),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


@app.get("/health")
def health():
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    if sys.argv[1:] == ["daily"]:
        run_daily()
    else:
        app.run(port=int(os.environ.get("PORT", 5050)), debug=True)
