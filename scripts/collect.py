"""
Claude API를 사용한 명언 수집 + PostgreSQL 저장.

사용법:
    python scripts/collect.py                    # 전체 카테고리 수집
    python scripts/collect.py --category 인생/삶  # 특정 카테고리만
    python scripts/collect.py --dry-run           # DB 저장 없이 확인만
"""

import argparse
import json
import os
import uuid

import anthropic
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SIMILARITY_THRESHOLD = 0.4

COLLECTION_PLAN = [
    {"category": "인생/삶", "count": 25, "prompt_hint": "인생, 삶의 의미, 존재, 죽음, 시간에 대한 명언"},
    {"category": "사랑/관계", "count": 15, "prompt_hint": "사랑, 우정, 가족, 인간관계에 대한 명언"},
    {"category": "동기부여/성공", "count": 15, "prompt_hint": "동기부여, 성공, 노력, 도전, 끈기에 대한 명언"},
    {"category": "유머/위트", "count": 10, "prompt_hint": "유머러스하고 위트 있는 명언, 재치 있는 인생 조언"},
    {"category": "공부/학습", "count": 10, "prompt_hint": "공부, 학습, 지식, 교육, 지혜에 대한 명언"},
    {"category": "고사성어", "count": 15, "prompt_hint": "유명한 고사성어와 그 유래, 사자성어"},
    {"category": "과학/철학", "count": 10, "prompt_hint": "과학자, 철학자의 명언. 진리, 탐구, 사고에 대한 문장"},
]


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        user=os.getenv("PG_USER", "youheaukjun"),
        password=os.getenv("PG_PASSWORD", ""),
        dbname=os.getenv("PG_DATABASE", "quotes_db"),
    )


# ---------------------------------------------------------------------------
# 마스터 목록 로드 + 프롬프트 생성
# ---------------------------------------------------------------------------

def load_master_lists():
    """DB에서 키워드, 상황, 직업, 분야 마스터 목록을 로드한다."""
    conn = get_db_connection()
    cur = conn.cursor()

    masters = {}
    for table, cols in [
        ("keywords", "name, group_name"),
        ("situations", "name, group_name"),
        ("professions", "name, group_name"),
        ("fields", "name"),
    ]:
        cur.execute(f"SELECT id, {cols} FROM {table} ORDER BY name")
        rows = cur.fetchall()
        if table == "fields":
            masters[table] = {r[1]: r[0] for r in rows}  # name → id
        else:
            masters[table] = {r[1]: {"id": r[0], "group": r[2]} for r in rows}  # name → {id, group}

    cur.close()
    conn.close()
    return masters


def build_system_prompt(masters: dict) -> str:
    """마스터 목록을 포함한 시스템 프롬프트를 생성한다."""

    kw_list = ", ".join(sorted(masters["keywords"].keys()))
    sit_list = ", ".join(sorted(masters["situations"].keys()))
    prof_list = ", ".join(sorted(masters["professions"].keys()))
    field_list = ", ".join(sorted(masters["fields"].keys()))

    return f"""너는 명언 데이터 큐레이터야. 요청받은 카테고리에 맞는 실존하는 유명 명언을 수집해줘.

중요한 규칙:
- 반드시 실제로 존재하는 명언만 제공해. 절대 지어내지 마.
- 출처를 알 수 없으면 source를 null로 해.
- 저자 정보를 최대한 정확하게 제공해.
- 한국어 번역과 원문을 모두 제공해.

키워드 태깅 규칙:
- 반드시 아래 목록에서만 선택해. 2~5개 선택.
- 사용 가능한 키워드: [{kw_list}]

상황 태깅 규칙:
- 반드시 아래 목록에서만 선택해. 1~3개 선택.
- 사용 가능한 상황: [{sit_list}]

저자 직업 규칙:
- 반드시 아래 목록에서만 선택해.
- 사용 가능한 직업: [{prof_list}]
- 목록에 없는 직업이면 가장 가까운 것을 선택하되, 정말 없으면 "_new:실제직업명" 형식으로 작성해.

저자 분야 규칙:
- 반드시 아래 목록에서만 선택해.
- 사용 가능한 분야: [{field_list}]
- 목록에 없는 분야면 "_new:실제분야명" 형식으로 작성해.

반드시 아래 JSON 형식으로만 응답해:

{{
  "quotes": [
    {{
      "text": "한국어 번역 텍스트",
      "text_original": "원문 (영어 등)",
      "original_language": "en",
      "source": "출처 (책, 연설 등) 또는 null",
      "year": 1929,
      "keywords": ["키워드1", "키워드2"],
      "situation": ["상황1", "상황2"],
      "author": {{
        "name": "저자 이름 (한국어)",
        "profession": "직업",
        "field": "분야",
        "nationality": "ISO 3166-1 alpha-2 국가코드 (예: KR, US, GB, DE, CN)",
        "birth_year": 1879,
        "relations": [
          {{"name": "관계 있는 저자 이름", "type": "mentor|influenced_by|contemporary"}}
        ]
      }}
    }}
  ]
}}

author.relations 규칙:
- 역사적으로 확인된 관계만. 추측 금지.
- mentor: 직접적인 스승→제자
- influenced_by: 사상적 영향을 준 사람→받은 사람
- contemporary: 같은 시대 교류
- 관계가 없으면 빈 배열 []"""


# ---------------------------------------------------------------------------
# Claude API 호출
# ---------------------------------------------------------------------------

def fetch_quotes_from_claude(category: str, count: int, prompt_hint: str, system_prompt: str) -> list[dict]:
    """Claude API로 명언을 수집한다."""
    client = anthropic.Anthropic()

    user_prompt = (
        f'"{category}" 카테고리에 해당하는 명언 {count}개를 수집해줘.\n'
        f"힌트: {prompt_hint}\n"
        f"다양한 시대, 국적, 분야의 저자를 포함해줘."
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text

    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    return json.loads(text)["quotes"]


# ---------------------------------------------------------------------------
# 저자 처리
# ---------------------------------------------------------------------------

def get_or_create_author(cursor, author_data: dict, masters: dict) -> str:
    """저자가 이미 존재하면 ID 반환, 없으면 생성 후 ID 반환."""
    cursor.execute("SELECT id FROM authors WHERE name = %s", (author_data["name"],))
    row = cursor.fetchone()
    if row:
        return row[0]

    # profession_id 찾기
    prof_name = author_data.get("profession", "")
    if prof_name.startswith("_new:"):
        prof_name = prof_name[5:]
        prof_id = _get_or_create_master(cursor, "professions", prof_name)
    else:
        prof_info = masters["professions"].get(prof_name)
        prof_id = prof_info["id"] if prof_info else _get_or_create_master(cursor, "professions", prof_name)

    # field_id 찾기
    field_name = author_data.get("field", "")
    if field_name.startswith("_new:"):
        field_name = field_name[5:]
        field_id = _get_or_create_master(cursor, "fields", field_name)
    else:
        field_id = masters["fields"].get(field_name)
        if not field_id:
            field_id = _get_or_create_master(cursor, "fields", field_name)

    author_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO authors (id, name, nationality, birth_year, profession_id, field_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            author_id,
            author_data["name"],
            author_data.get("nationality", ""),
            author_data.get("birth_year", 0),
            prof_id,
            field_id,
        ),
    )
    return author_id


def _get_or_create_master(cursor, table: str, name: str) -> str:
    """마스터 테이블에서 이름으로 ID를 찾고, 없으면 생성한다."""
    cursor.execute(f"SELECT id FROM {table} WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    new_id = str(uuid.uuid4())
    if table == "fields":
        cursor.execute(f"INSERT INTO {table} (id, name) VALUES (%s, %s)", (new_id, name))
    else:
        cursor.execute(f"INSERT INTO {table} (id, name) VALUES (%s, %s)", (new_id, name))
    print(f"  [NEW] {table}: {name}")
    return new_id


def save_author_relations(cursor, author_id: str, relations: list[dict]):
    """저자 간 관계를 저장한다."""
    for rel in relations:
        cursor.execute("SELECT id FROM authors WHERE name = %s", (rel["name"],))
        row = cursor.fetchone()
        if not row:
            continue

        other_id = row[0]
        rel_type = rel["type"]

        if rel_type in ("mentor", "influenced_by"):
            pairs = [(other_id, author_id)]
        else:
            pairs = [(author_id, other_id), (other_id, author_id)]

        for from_id, to_id in pairs:
            cursor.execute(
                """INSERT INTO author_relations (id, from_author_id, to_author_id, relation_type)
                VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                (str(uuid.uuid4()), from_id, to_id, rel_type),
            )


# ---------------------------------------------------------------------------
# 키워드/상황 ID 변환
# ---------------------------------------------------------------------------

def resolve_keyword_ids(cursor, keyword_names: list[str], masters: dict) -> list[str]:
    """키워드 이름 목록을 ID 목록으로 변환한다."""
    ids = set()
    for name in keyword_names:
        info = masters["keywords"].get(name)
        if info:
            ids.add(info["id"])
        else:
            new_id = _get_or_create_master(cursor, "keywords", name)
            ids.add(new_id)
    return list(ids)


def resolve_situation_ids(cursor, situation_names: list[str], masters: dict) -> list[str]:
    """상황 이름 목록을 ID 목록으로 변환한다."""
    ids = set()
    for name in situation_names:
        info = masters["situations"].get(name)
        if info:
            ids.add(info["id"])
        else:
            new_id = _get_or_create_master(cursor, "situations", name)
            ids.add(new_id)
    return list(ids)


# ---------------------------------------------------------------------------
# 중복 검사
# ---------------------------------------------------------------------------

def find_similar(cursor, text: str, text_original: str | None) -> tuple[bool, str | None]:
    """유사한 명언이 이미 존재하는지 확인한다."""
    if text_original:
        cursor.execute("SELECT text FROM quotes WHERE text_original = %s", (text_original,))
        row = cursor.fetchone()
        if row:
            return True, row[0]

    cursor.execute("SELECT text FROM quotes WHERE text = %s", (text,))
    row = cursor.fetchone()
    if row:
        return True, row[0]

    cursor.execute(
        "SELECT text, similarity(text, %s) AS sim FROM quotes WHERE similarity(text, %s) > %s ORDER BY sim DESC LIMIT 1",
        (text, text, SIMILARITY_THRESHOLD),
    )
    row = cursor.fetchone()
    if row:
        return True, row[0]

    if text_original:
        cursor.execute(
            "SELECT text, similarity(text_original, %s) AS sim FROM quotes WHERE text_original IS NOT NULL AND similarity(text_original, %s) > %s ORDER BY sim DESC LIMIT 1",
            (text_original, text_original, SIMILARITY_THRESHOLD),
        )
        row = cursor.fetchone()
        if row:
            return True, row[0]

    return False, None


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------

def determine_source_reliability(quote: dict) -> str:
    """출처 정보로 신뢰도를 판정한다."""
    source = quote.get("source")
    if not source:
        return "unknown"
    # 책, 연설, 서신 등 구체적 출처가 있으면 attributed
    return "attributed"


_NEED_MAP = {
    "motivation": {
        "keywords": {"끈기", "노력", "도전", "용기", "행동", "인내", "열정", "목표", "성공", "실패", "실천", "동기부여"},
        "situations": {"게으를 때", "꾸준함이 필요할 때", "목표가 멀게 느껴질 때", "포기하고 싶을 때", "도전을 망설일 때"},
    },
    "comfort": {
        "keywords": {"고통", "회복", "희망", "외로움", "두려움"},
        "situations": {"힘든 시기를 보낼 때", "절망적일 때", "좌절했을 때", "실패했을 때", "외로울 때", "희망이 필요할 때", "힘든 상황에서 거리를 두고 싶을 때", "불운할 때", "두려울 때"},
    },
    "reflection": {
        "keywords": {"철학", "존재", "자아", "의미", "자기성찰", "인생", "시간", "죽음", "운명", "선택", "초월"},
        "situations": {"자기 성찰", "삶의 의미를 찾을 때", "인생의 선택", "과거를 돌아볼 때", "죽음을 생각할 때", "현재를 살고 싶을 때", "변화를 마주할 때", "미래가 불안할 때"},
    },
    "insight": {
        "keywords": {"학습", "지식", "지혜", "겸손", "교육", "창의성"},
        "situations": {"배움의 자세", "지식의 가치", "깊이 이해하고 싶을 때", "공부하기 싫을 때", "새로운 관점이 필요할 때", "과학적 사고", "창의적 사고"},
    },
    "relationship": {
        "keywords": {"사랑", "관계", "우정", "가족", "헌신", "감사", "공동체"},
        "situations": {"관계의 소중함", "관계가 어려울 때", "사랑을 느낄 때", "사랑의 본질을 고민할 때", "감사할 때"},
    },
    "humor": {
        "keywords": {"유머", "위트"},
        "situations": {"웃음이 필요할 때", "일상의 소소함", "기분 전환이 필요할 때"},
    },
}


def _compute_need_types(keywords, situations):
    kws = set(keywords) if isinstance(keywords, list) else set()
    sits = set(situations) if isinstance(situations, list) else set()
    scores = {}
    for need, m in _NEED_MAP.items():
        score = len(kws & m["keywords"]) + len(sits & m["situations"]) * 2
        if score > 0:
            scores[need] = score
    if not scores:
        return ["reflection"]
    return [n for n, _ in sorted(scores.items(), key=lambda x: -x[1])[:3]]


def save_quotes(quotes: list[dict], masters: dict, dry_run: bool = False, collection_log_id: str | None = None) -> dict:
    """명언 목록을 PostgreSQL에 저장한다."""
    stats = {"saved": 0, "duplicates": 0, "errors": 0}

    if dry_run:
        for q in quotes:
            kws = q.get("keywords", [])
            sits = q.get("situation", [])
            rel = determine_source_reliability(q)
            print(f"  [{q['author']['name']}] {q['text'][:50]}...")
            print(f"    키워드: {kws}")
            print(f"    상황: {sits}")
            print(f"    출처 신뢰도: {rel}")
        stats["saved"] = len(quotes)
        return stats

    conn = get_db_connection()
    cursor = conn.cursor()

    for q in quotes:
        try:
            is_dup, existing = find_similar(cursor, q["text"], q.get("text_original"))
            if is_dup:
                print(f"  중복 스킵: \"{q['text'][:30]}...\" ≈ \"{existing[:30]}...\"")
                stats["duplicates"] += 1
                continue

            author_id = get_or_create_author(cursor, q["author"], masters)
            save_author_relations(cursor, author_id, q["author"].get("relations", []))

            keyword_ids = resolve_keyword_ids(cursor, q.get("keywords", []), masters)
            situation_ids = resolve_situation_ids(cursor, q.get("situation", []), masters)

            reliability = determine_source_reliability(q)
            need_types = _compute_need_types(q.get("keywords", []), q.get("situation", []))
            quote_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO quotes (id, text, text_original, original_language, author_id, source, year,
                   keywords, situation, keyword_ids, situation_ids, need_types, status, source_reliability, collection_log_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    quote_id,
                    q["text"],
                    q.get("text_original"),
                    q.get("original_language"),
                    author_id,
                    q.get("source"),
                    q.get("year"),
                    json.dumps(q.get("keywords", []), ensure_ascii=False),
                    json.dumps(q.get("situation", []), ensure_ascii=False),
                    keyword_ids,
                    situation_ids,
                    need_types,
                    "draft",
                    reliability,
                    collection_log_id,
                ),
            )
            stats["saved"] += 1
        except Exception as e:
            print(f"  오류: {e}")
            stats["errors"] += 1

    conn.commit()
    cursor.close()
    conn.close()
    return stats


# ---------------------------------------------------------------------------
# 수집 이력 로그
# ---------------------------------------------------------------------------

def create_collection_log(category: str, requested: int) -> str:
    """수집 시작 시 이력 레코드를 생성하고 ID를 반환한다."""
    conn = get_db_connection()
    cur = conn.cursor()
    log_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO collection_logs (id, category, requested_count, saved_count, duplicate_count, error_count)
        VALUES (%s, %s, %s, 0, 0, 0)""",
        (log_id, category, requested),
    )
    conn.commit()
    cur.close()
    conn.close()
    return log_id


def update_collection_log(log_id: str, stats: dict):
    """수집 완료 후 이력 레코드를 업데이트한다."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE collection_logs SET saved_count = %s, duplicate_count = %s, error_count = %s
        WHERE id = %s""",
        (stats["saved"], stats["duplicates"], stats["errors"], log_id),
    )
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def collect(category_filter: str | None = None, dry_run: bool = False):
    """수집 계획에 따라 명언을 수집한다."""
    masters = load_master_lists()
    system_prompt = build_system_prompt(masters)

    plan = COLLECTION_PLAN
    if category_filter:
        plan = [p for p in plan if p["category"] == category_filter]
        if not plan:
            print(f"카테고리 '{category_filter}'를 찾을 수 없습니다.")
            print(f"가능한 카테고리: {', '.join(p['category'] for p in COLLECTION_PLAN)}")
            return

    total_stats = {"saved": 0, "duplicates": 0, "errors": 0}

    for item in plan:
        category = item["category"]
        count = item["count"]
        print(f"\n{'='*50}")
        print(f"수집 중: {category} ({count}개)")
        print(f"{'='*50}")

        try:
            log_id = None
            if not dry_run:
                log_id = create_collection_log(category, count)

            quotes = fetch_quotes_from_claude(category, count, item["prompt_hint"], system_prompt)
            print(f"  Claude 응답: {len(quotes)}개")

            stats = save_quotes(quotes, masters, dry_run=dry_run, collection_log_id=log_id)
            print(f"  저장: {stats['saved']}개 | 중복: {stats['duplicates']}개 | 오류: {stats['errors']}개")

            if not dry_run:
                update_collection_log(log_id, stats)

            for key in total_stats:
                total_stats[key] += stats[key]

        except Exception as e:
            print(f"  수집 실패: {e}")
            total_stats["errors"] += 1

    print(f"\n{'='*50}")
    print(f"수집 완료!")
    print(f"  총 저장: {total_stats['saved']}개")
    print(f"  총 중복: {total_stats['duplicates']}개")
    print(f"  총 오류: {total_stats['errors']}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="매일 동기부여")
    parser.add_argument("--category", type=str, help="특정 카테고리만 수집")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 확인만")
    args = parser.parse_args()

    collect(category_filter=args.category, dry_run=args.dry_run)
