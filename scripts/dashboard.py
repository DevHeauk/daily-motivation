"""
명언 데이터 현황 대시보드.

사용법:
    python scripts/dashboard.py
    # 브라우저에서 http://localhost:5050 접속
"""

import glob
import json
import os
import uuid
from functools import wraps

import anthropic
import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, redirect
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
# 세션(서명 쿠키)용 시크릿. 미설정 시 ADMIN_TOKEN 기반으로 대체.
app.secret_key = os.getenv("SECRET_KEY") or os.getenv("ADMIN_TOKEN") or "dev-secret-change-me"
CORS(app)


def get_db():
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


def query(sql):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


@app.route("/api/stats")
def stats():
    conn = get_db()
    cur = conn.cursor()
    counts = {}
    for table in ["quotes", "authors", "author_relations", "keywords", "situations", "fields"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify(counts)


@app.route("/api/by-field")
def by_field():
    return jsonify(query("""
        SELECT f.name as field, COUNT(*) as count
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        JOIN fields f ON a.field_id = f.id
        GROUP BY f.name ORDER BY count DESC
    """))


@app.route("/api/by-nationality")
def by_nationality():
    return jsonify(query("""
        SELECT a.nationality, COUNT(*) as count
        FROM quotes q JOIN authors a ON q.author_id = a.id
        GROUP BY a.nationality ORDER BY count DESC
    """))


@app.route("/api/by-keyword")
def by_keyword():
    return jsonify(query("""
        SELECT k.name as keyword, k.group_name, COUNT(*) as count
        FROM quotes q, unnest(q.keyword_ids) AS kid
        JOIN keywords k ON k.id = kid
        GROUP BY k.name, k.group_name ORDER BY count DESC LIMIT 30
    """))


@app.route("/api/by-keyword-group")
def by_keyword_group():
    return jsonify(query("""
        SELECT COALESCE(k.group_name, '미분류') as group_name, COUNT(*) as count
        FROM quotes q, unnest(q.keyword_ids) AS kid
        JOIN keywords k ON k.id = kid
        GROUP BY k.group_name ORDER BY count DESC
    """))


@app.route("/api/by-situation")
def by_situation():
    return jsonify(query("""
        SELECT s.name as situation, s.group_name, COUNT(*) as count
        FROM quotes q, unnest(q.situation_ids) AS sid
        JOIN situations s ON s.id = sid
        GROUP BY s.name, s.group_name ORDER BY count DESC LIMIT 30
    """))


@app.route("/api/by-situation-group")
def by_situation_group():
    return jsonify(query("""
        SELECT COALESCE(s.group_name, '미분류') as group_name, COUNT(*) as count
        FROM quotes q, unnest(q.situation_ids) AS sid
        JOIN situations s ON s.id = sid
        GROUP BY s.group_name ORDER BY count DESC
    """))


@app.route("/api/by-profession")
def by_profession():
    return jsonify(query("""
        SELECT p.name as profession, p.group_name, COUNT(*) as count
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        JOIN professions p ON a.profession_id = p.id
        GROUP BY p.name, p.group_name ORDER BY count DESC
    """))


@app.route("/api/by-profession-group")
def by_profession_group():
    return jsonify(query("""
        SELECT COALESCE(p.group_name, '미분류') as group_name, COUNT(*) as count
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        JOIN professions p ON a.profession_id = p.id
        GROUP BY p.group_name ORDER BY count DESC
    """))


@app.route("/api/by-author")
def by_author():
    return jsonify(query("""
        SELECT a.name, f.name as field, p.name as profession, a.nationality, COUNT(*) as count
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        LEFT JOIN fields f ON a.field_id = f.id
        LEFT JOIN professions p ON a.profession_id = p.id
        GROUP BY a.id, a.name, f.name, p.name, a.nationality
        ORDER BY count DESC LIMIT 20
    """))


@app.route("/api/relations")
def relations():
    return jsonify(query("""
        SELECT
            a1.name as from_name, a2.name as to_name,
            ar.relation_type
        FROM author_relations ar
        JOIN authors a1 ON ar.from_author_id = a1.id
        JOIN authors a2 ON ar.to_author_id = a2.id
        ORDER BY ar.relation_type, a1.name
    """))


@app.route("/api/collection-history")
def collection_history():
    return jsonify(query("""
        SELECT category, requested_count, saved_count, duplicate_count, error_count,
               created_at::text
        FROM collection_logs
        ORDER BY created_at DESC LIMIT 30
    """))


@app.route("/api/verification-stats")
def verification_stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM quotes WHERE verified = TRUE")
    verified = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM quotes WHERE verified = FALSE")
    unverified = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify({"verified": verified, "unverified": unverified})


@app.route("/api/recent")
def recent():
    return jsonify(query("""
        SELECT q.text, a.name as author, q.keywords, q.created_at::text
        FROM quotes q JOIN authors a ON q.author_id = a.id
        ORDER BY q.created_at DESC LIMIT 10
    """))


@app.route("/api/trends")
def trends():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT fetched_at::text, timeframe, data FROM trends ORDER BY fetched_at DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "트렌드 데이터가 없습니다."}), 404
    result = row[2] if isinstance(row[2], dict) else json.loads(row[2])
    result["fetched_at"] = row[0]
    result["timeframe"] = row[1]
    return jsonify(result)


# ===========================================================================
# Admin API
# ===========================================================================

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_TOKEN:
            return jsonify({"error": "ADMIN_TOKEN not configured"}), 500
        # 웹 콘솔: 세션 로그인 / 모바일 앱·스크립트: Bearer 토큰
        auth = request.headers.get("Authorization", "")
        if session.get("admin") or auth == f"Bearer {ADMIN_TOKEN}":
            return f(*args, **kwargs)
        return jsonify({"error": "unauthorized"}), 401
    return decorated


@app.route("/admin/migrate", methods=["POST"])
def admin_migrate():
    """DB 마이그레이션 실행."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_interactions (
            id VARCHAR(36) PRIMARY KEY,
            device_id VARCHAR(64) NOT NULL,
            quote_id VARCHAR(36) NOT NULL REFERENCES quotes(id),
            interaction_type VARCHAR(20) NOT NULL,
            dwell_seconds FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interactions_device ON user_interactions(device_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interactions_created ON user_interactions(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interactions_device_type ON user_interactions(device_id, interaction_type)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id VARCHAR(36) PRIMARY KEY,
            device_id VARCHAR(64) NOT NULL UNIQUE,
            needs TEXT[] NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_preferences_device ON user_preferences(device_id)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_quotes (
            id VARCHAR(36) PRIMARY KEY,
            source VARCHAR(20) NOT NULL,
            text TEXT NOT NULL,
            author VARCHAR(200),
            source_url TEXT,
            tags TEXT[],
            upvotes INT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_raw_quotes_source ON raw_quotes(source)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_raw_quotes_status ON raw_quotes(status)")
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_quotes_dedup
        ON raw_quotes (source, md5(text))
    """)
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "migrated"})


@app.route("/admin/publish-all", methods=["POST"])
def admin_publish_all():
    """draft 상태 명언을 일괄 published로 변경."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE quotes SET status = 'published' WHERE status = 'draft'")
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"updated": count})


# ---------------------------------------------------------------------------
# Admin Console API — 명언 CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/api/quotes")
@require_admin
def admin_quotes_list():
    """명언 목록 (필터 + 페이지네이션)."""
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)
    offset = (page - 1) * limit

    where = []
    params = []

    status = request.args.get("status")
    if status:
        where.append("q.status = %s")
        params.append(status)

    keyword_group = request.args.get("keyword_group")
    if keyword_group:
        where.append("EXISTS (SELECT 1 FROM keywords k WHERE k.id = ANY(q.keyword_ids) AND k.group_name = %s)")
        params.append(keyword_group)

    reliability = request.args.get("reliability")
    if reliability:
        where.append("q.source_reliability = %s")
        params.append(reliability)

    search = request.args.get("search", "").strip()
    if search:
        where.append("(q.text ILIKE %s OR a.name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_clause = " AND ".join(where) if where else "1=1"

    conn = get_db()
    cur = conn.cursor()

    # total count
    cur.execute(f"""
        SELECT COUNT(*) FROM quotes q
        JOIN authors a ON q.author_id = a.id
        WHERE {where_clause}
    """, params)
    total = cur.fetchone()[0]

    cur.execute(f"""
        SELECT q.id, q.text, q.text_original, q.original_language, q.source, q.year,
               q.status, q.source_reliability, q.created_at::text,
               q.keyword_ids, q.situation_ids,
               a.id as author_id, a.name as author_name,
               ARRAY(SELECT k.name FROM keywords k WHERE k.id = ANY(q.keyword_ids)) as keywords,
               ARRAY(SELECT s.name FROM situations s WHERE s.id = ANY(q.situation_ids)) as situations
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        WHERE {where_clause}
        ORDER BY q.created_at DESC
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"quotes": rows, "total": total, "page": page, "limit": limit})


@app.route("/admin/api/quotes", methods=["POST"])
@require_admin
def admin_quotes_create():
    """명언 추가."""
    data = request.get_json()
    text = data.get("text", "").strip()
    author_id = data.get("author_id", "").strip()
    if not text or not author_id:
        return jsonify({"error": "text and author_id required"}), 400

    qid = str(uuid.uuid4())
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO quotes (id, text, text_original, original_language, author_id,
                            source, year, keywords, situation, keyword_ids, situation_ids,
                            status, source_reliability)
        VALUES (%s, %s, %s, %s, %s, %s, %s, '[]'::jsonb, '[]'::jsonb, %s, %s, %s, %s)
    """, (
        qid, text,
        data.get("text_original") or None,
        data.get("original_language") or None,
        author_id,
        data.get("source") or None,
        data.get("year") or None,
        data.get("keyword_ids") or [],
        data.get("situation_ids") or [],
        data.get("status", "draft"),
        data.get("source_reliability", "unknown"),
    ))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": qid}), 201


@app.route("/admin/api/quotes/<quote_id>", methods=["PATCH"])
@require_admin
def admin_quotes_update(quote_id):
    """명언 개별 수정 (변경 필드만)."""
    data = request.get_json()
    allowed = {"text", "text_original", "original_language", "author_id",
               "source", "year", "status", "source_reliability",
               "keyword_ids", "situation_ids", "impact_score"}
    sets = []
    params = []
    for key, val in data.items():
        if key in allowed:
            sets.append(f"{key} = %s")
            params.append(val)
    if not sets:
        return jsonify({"error": "no valid fields"}), 400

    params.append(quote_id)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE quotes SET {', '.join(sets)} WHERE id = %s", params)
    if cur.rowcount == 0:
        cur.close(); conn.close()
        return jsonify({"error": "not found"}), 404
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"updated": True})


@app.route("/admin/api/quotes/<quote_id>/retranslate", methods=["POST"])
@require_admin
def admin_quotes_retranslate(quote_id):
    """원문을 LLM으로 재번역해 text를 갱신하고 status를 draft로 초기화."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT q.text_original, q.original_language, a.name "
        "FROM quotes q JOIN authors a ON q.author_id = a.id WHERE q.id = %s",
        (quote_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({"error": "not found"}), 404
    text_original, original_language, author_name = row
    if not text_original:
        cur.close(); conn.close()
        return jsonify({"error": "원문(text_original)이 없어 재번역할 수 없습니다"}), 400

    # 방향 자동: 원문이 한국어면 영어로, 그 외(영어 등)면 한국어로 번역
    target = "en" if original_language == "ko" else "ko"
    target_name = "영어" if target == "en" else "한국어"

    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            system=(
                f"너는 명언 전문 번역가다. 주어진 원문 명언의 의미를 자연스럽게 살리도록 "
                f"{target_name}로 번역한다. 원문의 말맛·수사·뉘앙스를 보존하되 의역이 과하지 않게 한다. "
                f"설명·따옴표 없이 번역문 한 줄만 출력한다."
            ),
            messages=[{
                "role": "user",
                "content": f"저자: {author_name}\n원문({original_language}): {text_original}\n\n{target_name} 번역:",
            }],
        )
        new_text = msg.content[0].text.strip().strip('"“”')
    except Exception as e:
        cur.close(); conn.close()
        return jsonify({"error": f"번역 실패: {e}"}), 502

    cur.execute(
        "UPDATE quotes SET text = %s, status = 'draft' WHERE id = %s",
        (new_text, quote_id),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"text": new_text, "status": "draft", "target": target})


def _login_page(error=""):
    """관리자 로그인 화면 HTML."""
    err_html = f'<p class="err">{error}</p>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>관리자 로그인</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#0f1115; color:#e6e8ec;
         font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;
         padding:max(20px,env(safe-area-inset-top)) 20px; }}
  .box {{ width:100%; max-width:360px; background:#1a1d24; border:1px solid #232733;
         border-radius:16px; padding:32px 28px; }}
  h1 {{ font-size:20px; margin:0 0 6px; }}
  p.sub {{ color:#8a909c; font-size:13px; margin:0 0 24px; }}
  label {{ display:block; font-size:12px; color:#8a909c; margin-bottom:8px; }}
  input {{ width:100%; background:#0f1115; color:#e6e8ec; border:1px solid #2c313c;
          border-radius:10px; padding:13px 14px; font-size:15px; min-height:46px;
          font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  input:focus {{ outline:none; border-color:#5b9dff; }}
  button {{ width:100%; margin-top:16px; background:#5b9dff; color:#0f1115; border:none;
           border-radius:10px; padding:14px; font-size:15px; font-weight:700; cursor:pointer;
           min-height:48px; }}
  button:active {{ opacity:.85; }}
  .err {{ color:#ff8a8a; font-size:13px; margin:14px 0 0; }}
</style>
</head>
<body>
  <form class="box" method="POST" action="/admin/login">
    <h1>관리자 로그인</h1>
    <p class="sub">명언 관리 콘솔에 접근하려면 토큰을 입력하세요.</p>
    <label for="token">ADMIN_TOKEN</label>
    <input id="token" name="token" type="password" autocomplete="current-password"
           autocapitalize="off" autocorrect="off" spellcheck="false"
           placeholder="토큰을 입력하세요" autofocus>
    <button type="submit">로그인</button>
    {err_html}
  </form>
</body>
</html>"""


@app.route("/admin/login", methods=["POST"])
def admin_login():
    """토큰 검증 후 세션 로그인."""
    if not ADMIN_TOKEN:
        return _login_page("ADMIN_TOKEN이 설정되지 않았습니다."), 500
    token = (request.form.get("token") or "").strip()
    if token == ADMIN_TOKEN:
        session["admin"] = True
        return redirect("/admin")
    return _login_page("토큰이 올바르지 않습니다."), 401


@app.route("/admin/logout")
def admin_logout():
    """세션 로그아웃."""
    session.pop("admin", None)
    return redirect("/admin")


@app.route("/admin")
def admin_console():
    """관리자 콘솔 = 저자별 명언 카드 리포트를 서빙한다.

    세션 로그인(토큰 입력)이 있어야 화면이 보인다.
    동일 출처에서 열려야 카드의 상태/재번역 버튼이 admin API를 호출할 수 있다.
    정적 파일이 없으면(또는 `?refresh=1`이면) 현재 DB로 즉석 생성한다.
    """
    if not session.get("admin"):
        return _login_page()
    path = os.path.join(os.path.dirname(__file__), "..", "data", "reports", "authors.html")
    if request.args.get("refresh") or not os.path.exists(path):
        try:
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            import visualize_authors
            html = visualize_authors.build_html()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            return (f"리포트 생성 실패: {e}", 500)
    with open(path, encoding="utf-8") as f:
        return f.read()


@app.route("/admin/api/quotes/<quote_id>", methods=["DELETE"])
@require_admin
def admin_quotes_delete(quote_id):
    """명언 삭제 (interaction cascade)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_interactions WHERE quote_id = %s", (quote_id,))
    cur.execute("DELETE FROM quotes WHERE id = %s", (quote_id,))
    if cur.rowcount == 0:
        cur.close(); conn.close()
        return jsonify({"error": "not found"}), 404
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"deleted": True})


@app.route("/admin/api/quotes/batch-status", methods=["POST"])
@require_admin
def admin_quotes_batch_status():
    """일괄 상태 변경."""
    data = request.get_json()
    ids = data.get("ids", [])[:200]
    status = data.get("status", "")
    if not ids or status not in ("draft", "reviewed", "published", "rejected"):
        return jsonify({"error": "ids and valid status required"}), 400

    conn = get_db()
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(ids))
    cur.execute(f"UPDATE quotes SET status = %s WHERE id IN ({placeholders})", [status] + ids)
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"updated": count})


@app.route("/admin/api/quotes/batch-delete", methods=["POST"])
@require_admin
def admin_quotes_batch_delete():
    """일괄 삭제."""
    data = request.get_json()
    ids = data.get("ids", [])[:200]
    if not ids:
        return jsonify({"error": "ids required"}), 400

    conn = get_db()
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(ids))
    cur.execute(f"DELETE FROM user_interactions WHERE quote_id IN ({placeholders})", ids)
    cur.execute(f"DELETE FROM quotes WHERE id IN ({placeholders})", ids)
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"deleted": count})


# ---------------------------------------------------------------------------
# Admin Console API — 저자 CRUD
# ---------------------------------------------------------------------------

@app.route("/admin/api/authors")
@require_admin
def admin_authors_list():
    """저자 목록 (검색 + 페이지네이션)."""
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)
    offset = (page - 1) * limit
    search = request.args.get("search", "").strip()

    where = []
    params = []
    if search:
        where.append("a.name ILIKE %s")
        params.append(f"%{search}%")
    where_clause = " AND ".join(where) if where else "1=1"

    conn = get_db()
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM authors a WHERE {where_clause}", params)
    total = cur.fetchone()[0]

    cur.execute(f"""
        SELECT a.id, a.name, a.nationality, a.birth_year,
               p.id as profession_id, p.name as profession,
               f.id as field_id, f.name as field,
               COUNT(q.id) as quote_count
        FROM authors a
        LEFT JOIN professions p ON a.profession_id = p.id
        LEFT JOIN fields f ON a.field_id = f.id
        LEFT JOIN quotes q ON q.author_id = a.id
        WHERE {where_clause}
        GROUP BY a.id, a.name, a.nationality, a.birth_year, p.id, p.name, f.id, f.name
        ORDER BY quote_count DESC, a.name
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"authors": rows, "total": total, "page": page, "limit": limit})


@app.route("/admin/api/authors", methods=["POST"])
@require_admin
def admin_authors_create():
    """저자 추가."""
    data = request.get_json()
    name = data.get("name", "").strip()
    nationality = data.get("nationality", "").strip()
    birth_year = data.get("birth_year")
    if not name or not nationality or birth_year is None:
        return jsonify({"error": "name, nationality, birth_year required"}), 400

    aid = str(uuid.uuid4())
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO authors (id, name, nationality, birth_year, profession_id, field_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (aid, name, nationality, birth_year,
          data.get("profession_id") or None,
          data.get("field_id") or None))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": aid}), 201


@app.route("/admin/api/authors/<author_id>", methods=["PATCH"])
@require_admin
def admin_authors_update(author_id):
    """저자 수정."""
    data = request.get_json()
    allowed = {"name", "nationality", "birth_year", "profession_id", "field_id"}
    sets = []
    params = []
    for key, val in data.items():
        if key in allowed:
            sets.append(f"{key} = %s")
            params.append(val)
    if not sets:
        return jsonify({"error": "no valid fields"}), 400

    params.append(author_id)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"UPDATE authors SET {', '.join(sets)} WHERE id = %s", params)
    if cur.rowcount == 0:
        cur.close(); conn.close()
        return jsonify({"error": "not found"}), 404
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"updated": True})


@app.route("/admin/api/authors/<author_id>/preview-delete")
@require_admin
def admin_authors_preview_delete(author_id):
    """저자 삭제 영향 미리보기."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM quotes WHERE author_id = %s", (author_id,))
    quote_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM author_relations WHERE from_author_id = %s OR to_author_id = %s",
                (author_id, author_id))
    relation_count = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM user_interactions
        WHERE quote_id IN (SELECT id FROM quotes WHERE author_id = %s)
    """, (author_id,))
    interaction_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify({
        "quote_count": quote_count,
        "relation_count": relation_count,
        "interaction_count": interaction_count,
    })


@app.route("/admin/api/authors/<author_id>", methods=["DELETE"])
@require_admin
def admin_authors_delete(author_id):
    """저자 + 소속 명언 + 관계 + interaction 전부 삭제."""
    conn = get_db()
    cur = conn.cursor()
    # 1. interaction 삭제 (해당 저자 명언의)
    cur.execute("""
        DELETE FROM user_interactions
        WHERE quote_id IN (SELECT id FROM quotes WHERE author_id = %s)
    """, (author_id,))
    i_count = cur.rowcount
    # 2. 명언 삭제
    cur.execute("DELETE FROM quotes WHERE author_id = %s", (author_id,))
    q_count = cur.rowcount
    # 3. 관계 삭제
    cur.execute("DELETE FROM author_relations WHERE from_author_id = %s OR to_author_id = %s",
                (author_id, author_id))
    r_count = cur.rowcount
    # 4. 저자 삭제
    cur.execute("DELETE FROM authors WHERE id = %s", (author_id,))
    if cur.rowcount == 0:
        conn.rollback()
        cur.close(); conn.close()
        return jsonify({"error": "not found"}), 404
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({
        "deleted_quotes": q_count,
        "deleted_relations": r_count,
        "deleted_interactions": i_count,
    })


# ---------------------------------------------------------------------------
# Admin Console API — 마스터 데이터
# ---------------------------------------------------------------------------

@app.route("/admin/api/masters/keywords")
@require_admin
def admin_masters_keywords():
    return jsonify(query("SELECT id, name, group_name FROM keywords ORDER BY group_name, name"))


@app.route("/admin/api/masters/situations")
@require_admin
def admin_masters_situations():
    return jsonify(query("SELECT id, name, group_name FROM situations ORDER BY group_name, name"))


@app.route("/admin/api/masters/professions")
@require_admin
def admin_masters_professions():
    return jsonify(query("SELECT id, name, group_name FROM professions ORDER BY group_name, name"))


@app.route("/admin/api/masters/fields")
@require_admin
def admin_masters_fields():
    return jsonify(query("SELECT id, name FROM fields ORDER BY name"))


@app.route("/admin/api/raw-quotes", methods=["POST"])
@require_admin
def admin_raw_quotes_bulk():
    """raw_quotes 테이블에 벌크 INSERT."""
    data = request.get_json()
    items = data.get("quotes", [])
    if not items:
        return jsonify({"error": "quotes array required"}), 400
    conn = get_db()
    cur = conn.cursor()
    saved = 0
    dupes = 0
    for q in items:
        text = (q.get("text") or "").strip()
        if not text:
            continue
        try:
            cur.execute("""
                INSERT INTO raw_quotes (id, source, text, author, source_url, tags, upvotes, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                ON CONFLICT (source, md5(text)) DO NOTHING
            """, (str(uuid.uuid4()), q.get("source", "unknown"), text,
                  q.get("author"), q.get("source_url"),
                  q.get("tags"), q.get("upvotes")))
            if cur.rowcount > 0:
                saved += 1
            else:
                dupes += 1
        except psycopg2.Error:
            conn.rollback()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"saved": saved, "dupes": dupes, "total": len(items)})


@app.route("/admin/api/raw-quotes")
@require_admin
def admin_raw_quotes_list():
    """raw_quotes 목록 조회."""
    source = request.args.get("source")
    status = request.args.get("status", "pending")
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT id, source, text, author, source_url, tags, upvotes, status, created_at FROM raw_quotes WHERE status = %s"
    params = [status]
    if source:
        sql += " AND source = %s"
        params.append(source)
    sql += " ORDER BY created_at DESC LIMIT 200"
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return jsonify({"quotes": rows, "total": len(rows)})


@app.route("/admin/api/sync", methods=["POST"])
@require_admin
def admin_sync():
    """로컬 DB → 프로덕션 동기화. authors + quotes upsert."""
    data = request.get_json()
    authors = data.get("authors", [])
    quotes_data = data.get("quotes", [])

    conn = get_db()
    cur = conn.cursor()

    # 1) professions/fields upsert
    for table in ("professions", "fields"):
        for item in data.get(table, []):
            cur.execute(f"""
                INSERT INTO {table} (id, name) VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (item["id"], item["name"]))

    # 2) authors upsert
    author_saved = 0
    for a in authors:
        cur.execute("""
            INSERT INTO authors (id, name, nationality, birth_year, profession_id, field_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                nationality = EXCLUDED.nationality,
                birth_year = EXCLUDED.birth_year,
                profession_id = EXCLUDED.profession_id,
                field_id = EXCLUDED.field_id
        """, (a["id"], a["name"], a.get("nationality", ""),
              a.get("birth_year", 0), a.get("profession_id"), a.get("field_id")))
        author_saved += 1

    # 3) quotes upsert
    quote_saved = 0
    for q in quotes_data:
        cur.execute("""
            INSERT INTO quotes (id, text, text_original, original_language, author_id, source,
                keywords, situation, keyword_ids, situation_ids, need_types,
                impact_score, status, source_reliability, collection_log_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                text = EXCLUDED.text,
                impact_score = EXCLUDED.impact_score,
                status = EXCLUDED.status,
                keyword_ids = EXCLUDED.keyword_ids,
                situation_ids = EXCLUDED.situation_ids,
                need_types = EXCLUDED.need_types
        """, (
            q["id"], q["text"], q.get("text_original"), q.get("original_language"),
            q["author_id"], q.get("source"),
            q.get("keywords", "[]"), q.get("situation", "[]"),
            q.get("keyword_ids", []), q.get("situation_ids", []),
            q.get("need_types", []), q.get("impact_score", 3),
            q.get("status", "draft"), q.get("source_reliability", "unknown"),
            q.get("collection_log_id"),
        ))
        quote_saved += 1

    # 4) 프로덕션에만 있고 로컬에서 삭제된 quotes 처리
    delete_ids = data.get("delete_quote_ids", [])
    deleted = 0
    for qid in delete_ids:
        cur.execute("DELETE FROM quotes WHERE id = %s", (qid,))
        deleted += cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"authors": author_saved, "quotes": quote_saved, "deleted": deleted})


# ===========================================================================
# App API (모바일 앱 전용)
# ===========================================================================

def _quote_to_dict(row, cols):
    """쿼리 결과를 앱용 dict로 변환."""
    d = dict(zip(cols, row))
    for k in ("keywords", "situations"):
        if k in d and isinstance(d[k], str):
            d[k] = json.loads(d[k])
    return d


def _build_personalization(args):
    """개인화 파라미터에서 WHERE/ORDER BY 조건과 params를 빌드.

    needs 파라미터(신규): need_types 배열 매칭 보너스 (1차 시그널).
    situations/keywords(레거시): 기존 그룹 매칭 보너스 (2차 시그널).
    프로필 가중치(kw_weights, sit_weights): 행동 기반 보너스 (3차 시그널).
    profile_strength에 따라 온보딩/행동 비율을 혼합한다.
    """
    needs_raw = args.get("needs", "")
    sit_groups = args.get("situations", "")
    kw_groups = args.get("keywords", "")
    exclude_ids = args.get("exclude", "")
    needs_list = [n.strip() for n in needs_raw.split(",") if n.strip()]
    sit_list = [s.strip() for s in sit_groups.split(",") if s.strip()]
    kw_list = [k.strip() for k in kw_groups.split(",") if k.strip()]
    exclude_list = [e.strip() for e in exclude_ids.split(",") if e.strip()]

    # 프로필 가중치 파싱
    kw_weights = {}
    sit_weights = {}
    profile_strength = args.get("profile_strength", "")
    try:
        raw = args.get("kw_weights", "")
        if raw:
            kw_weights = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        raw = args.get("sit_weights", "")
        if raw:
            sit_weights = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # 콜드 스타트 혼합 비율: 행동 비율 결정
    behavior_ratio = {"weak": 0.3, "moderate": 0.7, "strong": 1.0}.get(profile_strength, 0.0)
    onboarding_ratio = 1.0 - behavior_ratio

    params = []
    bonus_clauses = []
    where_clauses = []

    # 1차: need_types 매칭 보너스 (가장 강한 시그널)
    if needs_list and onboarding_ratio > 0:
        bonus_clauses.append(f"""
            CASE WHEN q.need_types && %s::varchar[]
            THEN {4 * onboarding_ratio:.2f} ELSE 0 END
        """)
        params.append(needs_list)

    # 2차: 레거시 온보딩 보너스 (하위 호환)
    if sit_list and onboarding_ratio > 0:
        bonus_clauses.append(f"""
            CASE WHEN EXISTS (
                SELECT 1 FROM situations s
                WHERE s.id = ANY(q.situation_ids) AND s.group_name = ANY(%s)
            ) THEN {3 * onboarding_ratio:.2f} ELSE 0 END
        """)
        params.append(sit_list)

    if kw_list and onboarding_ratio > 0:
        bonus_clauses.append(f"""
            CASE WHEN EXISTS (
                SELECT 1 FROM keywords k
                WHERE k.id = ANY(q.keyword_ids) AND k.group_name = ANY(%s)
            ) THEN {2 * onboarding_ratio:.2f} ELSE 0 END
        """)
        params.append(kw_list)

    # 3차: 행동 기반 동적 보너스 (프로필 가중치 × 5 × behavior_ratio)
    if kw_weights and behavior_ratio > 0:
        for group_name, weight in kw_weights.items():
            bonus_val = weight * 5 * behavior_ratio
            if bonus_val > 0.1:
                bonus_clauses.append(f"""
                    CASE WHEN EXISTS (
                        SELECT 1 FROM keywords k
                        WHERE k.id = ANY(q.keyword_ids) AND k.group_name = %s
                    ) THEN {bonus_val:.2f} ELSE 0 END
                """)
                params.append(group_name)

    if sit_weights and behavior_ratio > 0:
        for group_name, weight in sit_weights.items():
            bonus_val = weight * 5 * behavior_ratio
            if bonus_val > 0.1:
                bonus_clauses.append(f"""
                    CASE WHEN EXISTS (
                        SELECT 1 FROM situations s
                        WHERE s.id = ANY(q.situation_ids) AND s.group_name = %s
                    ) THEN {bonus_val:.2f} ELSE 0 END
                """)
                params.append(group_name)

    if exclude_list:
        where_clauses.append("q.id != ALL(%s)")
        params.append(exclude_list)

    bonus_sql = " + ".join(bonus_clauses) if bonus_clauses else "0"
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    return params, bonus_sql, where_sql


@app.route("/app/api/v1/interactions", methods=["POST"])
def app_interactions():
    """사용자 행동 로그 배치 업로드."""
    data = request.get_json()
    device_id = data.get("device_id", "")
    interactions = data.get("interactions", [])
    if not device_id or not interactions:
        return jsonify({"error": "device_id and interactions required"}), 400

    conn = get_db()
    cur = conn.cursor()
    saved = 0
    for item in interactions[:100]:  # 한 번에 최대 100개
        qid = item.get("quote_id", "")
        itype = item.get("type", "")
        if not qid or itype not in ("like", "unlike", "share", "view_detail", "dwell"):
            continue
        dwell_sec = None
        if itype == "dwell":
            dwell_sec = item.get("metadata", {}).get("dwell_seconds")
        ts = item.get("timestamp")
        try:
            cur.execute("""
                INSERT INTO user_interactions (id, device_id, quote_id, interaction_type, dwell_seconds, created_at)
                VALUES (%s, %s, %s, %s, %s, COALESCE(%s::timestamp, CURRENT_TIMESTAMP))
            """, (str(uuid.uuid4()), device_id, qid, itype, dwell_sec, ts))
            saved += 1
        except psycopg2.Error:
            conn.rollback()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"saved": saved})


@app.route("/app/api/v1/preferences", methods=["POST"])
def app_save_preferences():
    """사용자 온보딩 선호도 저장 (upsert)."""
    data = request.get_json()
    device_id = data.get("device_id", "")
    needs = data.get("needs", [])
    if not device_id or not isinstance(needs, list):
        return jsonify({"error": "device_id and needs required"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_preferences (id, device_id, needs, created_at, updated_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (device_id) DO UPDATE SET needs = %s, updated_at = CURRENT_TIMESTAMP
    """, (str(uuid.uuid4()), device_id, needs, needs))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "saved"})


@app.route("/app/api/v1/preferences")
def app_get_preferences():
    """사용자 온보딩 선호도 조회."""
    device_id = request.args.get("device_id", "")
    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT needs, created_at, updated_at FROM user_preferences WHERE device_id = %s", (device_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"needs": None})
    return jsonify({"needs": row[0], "created_at": row[1].isoformat(), "updated_at": row[2].isoformat()})


@app.route("/app/api/v1/profile")
def app_profile():
    """사용자 행동 기반 선호 프로필 계산.

    확신 시그널(like, share)만 프로필에 직접 반영.
    참고 시그널(dwell, view_detail)은 같은 quote에 확신 시그널이 있을 때만 증폭.
    """
    device_id = request.args.get("device_id", "")
    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    conn = get_db()
    cur = conn.cursor()

    # 1. 확신 시그널 조회 (like, unlike, share) + 시간 감쇠
    cur.execute("""
        SELECT quote_id, interaction_type,
               CASE
                   WHEN created_at > NOW() - INTERVAL '7 days' THEN 1.0
                   WHEN created_at > NOW() - INTERVAL '30 days' THEN 0.5
                   WHEN created_at > NOW() - INTERVAL '90 days' THEN 0.25
                   ELSE 0.1
               END as decay
        FROM user_interactions
        WHERE device_id = %s AND interaction_type IN ('like', 'unlike', 'share')
        ORDER BY created_at
    """, (device_id,))
    conviction_rows = cur.fetchall()

    if not conviction_rows:
        cur.close()
        conn.close()
        return jsonify({
            "keyword_weights": {},
            "situation_weights": {},
            "total_interactions": 0,
            "profile_strength": "weak",
        })

    # 확신 시그널이 있는 quote_id 집합
    conviction_quotes = set()
    # quote별 확신 점수 집계 (like=3, share=5, unlike=-3)
    quote_scores = {}
    score_map = {"like": 3.0, "share": 5.0, "unlike": -3.0}
    for qid, itype, decay in conviction_rows:
        conviction_quotes.add(qid)
        base = score_map.get(itype, 0)
        quote_scores[qid] = quote_scores.get(qid, 0) + base * decay

    # 2. 참고 시그널 조회 (확신 시그널이 있는 quote만)
    if conviction_quotes:
        placeholders = ",".join(["%s"] * len(conviction_quotes))
        cur.execute(f"""
            SELECT quote_id, interaction_type
            FROM user_interactions
            WHERE device_id = %s AND quote_id IN ({placeholders})
              AND interaction_type IN ('dwell', 'view_detail')
        """, [device_id] + list(conviction_quotes))
        ref_rows = cur.fetchall()

        # quote별 증폭 계수
        quote_boost = {}
        for qid, itype in ref_rows:
            if qid not in quote_boost:
                quote_boost[qid] = 1.0
            if itype == "dwell":
                quote_boost[qid] *= 1.5
            elif itype == "view_detail":
                quote_boost[qid] *= 1.3

        # 증폭 적용
        for qid, boost in quote_boost.items():
            if qid in quote_scores:
                quote_scores[qid] *= boost

    # 음수 점수인 quote 제거 (unlike으로 상쇄)
    quote_scores = {qid: s for qid, s in quote_scores.items() if s > 0}

    if not quote_scores:
        cur.close()
        conn.close()
        total = len(conviction_rows)
        return jsonify({
            "keyword_weights": {},
            "situation_weights": {},
            "total_interactions": total,
            "profile_strength": "weak" if total < 5 else "moderate",
        })

    # 3. quote별 keyword/situation 가져오기
    qids = list(quote_scores.keys())
    placeholders = ",".join(["%s"] * len(qids))
    cur.execute(f"""
        SELECT q.id,
               ARRAY(SELECT k.group_name FROM keywords k WHERE k.id = ANY(q.keyword_ids)) as kw_groups,
               ARRAY(SELECT s.group_name FROM situations s WHERE s.id = ANY(q.situation_ids)) as sit_groups
        FROM quotes q WHERE q.id IN ({placeholders})
    """, qids)

    kw_totals = {}
    sit_totals = {}
    for qid, kw_groups, sit_groups in cur.fetchall():
        score = quote_scores.get(qid, 0)
        if score <= 0:
            continue
        for g in (kw_groups or []):
            if g:
                kw_totals[g] = kw_totals.get(g, 0) + score
        for g in (sit_groups or []):
            if g:
                sit_totals[g] = sit_totals.get(g, 0) + score

    cur.close()
    conn.close()

    # 4. 정규화 (최대값 대비 0~1)
    def normalize(d):
        if not d:
            return {}
        mx = max(d.values())
        if mx <= 0:
            return {}
        return {k: round(v / mx, 3) for k, v in d.items()}

    kw_weights = normalize(kw_totals)
    sit_weights = normalize(sit_totals)

    total = len(conviction_rows)
    if total >= 20:
        strength = "strong"
    elif total >= 5:
        strength = "moderate"
    else:
        strength = "weak"

    return jsonify({
        "keyword_weights": kw_weights,
        "situation_weights": sit_weights,
        "total_interactions": total,
        "profile_strength": strength,
    })


@app.route("/app/api/v1/daily")
def app_daily():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT setseed(extract(doy from current_date)::float / 366.0)")

    params, bonus_sql, where_sql = _build_personalization(request.args)

    cur.execute(f"""
        SELECT q.id, q.text, q.text_original, q.original_language, q.source, q.year, q.impact_score,
               a.name as author_name, p.name as profession, f.name as field, a.nationality, a.birth_year,
               ARRAY(SELECT k.name FROM keywords k WHERE k.id = ANY(q.keyword_ids)) as keywords,
               ARRAY(SELECT s.name FROM situations s WHERE s.id = ANY(q.situation_ids)) as situations
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        LEFT JOIN professions p ON a.profession_id = p.id
        LEFT JOIN fields f ON a.field_id = f.id
        WHERE q.status = 'published' AND {where_sql}
        ORDER BY (COALESCE(q.impact_score, 3) + {bonus_sql}) * random()
        DESC LIMIT 1
    """, params)
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "명언이 없습니다."}), 404
    d = dict(zip(cols, row))
    return jsonify({
        "id": d["id"], "text": d["text"], "text_original": d["text_original"],
        "original_language": d["original_language"], "source": d["source"],
        "year": d["year"], "impact_score": d["impact_score"],
        "keywords": d["keywords"] or [], "situations": d["situations"] or [],
        "author": {
            "name": d["author_name"], "profession": d["profession"],
            "field": d["field"], "nationality": d["nationality"], "birth_year": d["birth_year"],
        },
    })


@app.route("/app/api/v1/recommend")
def app_recommend():
    """개인화 추천 명언 N개 반환."""
    conn = get_db()
    cur = conn.cursor()

    limit = min(request.args.get("limit", 3, type=int), 20)
    params, bonus_sql, where_sql = _build_personalization(request.args)
    params.append(limit)

    cur.execute(f"""
        SELECT q.id, q.text, q.text_original, q.original_language, q.source, q.impact_score,
               q.need_types,
               a.name as author_name, p.name as profession, a.nationality,
               ARRAY(SELECT k.name FROM keywords k WHERE k.id = ANY(q.keyword_ids)) as keywords,
               ARRAY(SELECT s.name FROM situations s WHERE s.id = ANY(q.situation_ids)) as situations
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        LEFT JOIN professions p ON a.profession_id = p.id
        WHERE q.status = 'published' AND {where_sql}
        ORDER BY (COALESCE(q.impact_score, 3) + {bonus_sql}) * random()
        DESC LIMIT %s
    """, params)
    cols = [d[0] for d in cur.description]
    rows = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        rows.append({
            "id": d["id"], "text": d["text"], "text_original": d["text_original"],
            "original_language": d["original_language"], "source": d["source"],
            "impact_score": d["impact_score"],
            "need_types": d["need_types"] or [],
            "keywords": d["keywords"] or [], "situations": d["situations"] or [],
            "author": {
                "name": d["author_name"], "profession": d["profession"],
                "nationality": d["nationality"],
            },
        })
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route("/app/api/v1/categories")
def app_categories():
    return jsonify(query("""
        SELECT k.group_name, ARRAY_AGG(DISTINCT k.name) as keywords,
               COUNT(DISTINCT qk) as count
        FROM keywords k
        LEFT JOIN quotes q ON k.id = ANY(q.keyword_ids)
        LEFT JOIN unnest(q.keyword_ids) AS qk ON true
        GROUP BY k.group_name
        ORDER BY count DESC
    """))


@app.route("/app/api/v1/situations")
def app_situations():
    return jsonify(query("""
        SELECT s.group_name, ARRAY_AGG(DISTINCT s.name) as situations,
               COUNT(DISTINCT qs) as count
        FROM situations s
        LEFT JOIN quotes q ON s.id = ANY(q.situation_ids)
        LEFT JOIN unnest(q.situation_ids) AS qs ON true
        GROUP BY s.group_name
        ORDER BY count DESC
    """))


@app.route("/app/api/v1/authors")
def app_authors():
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 50)
    offset = (page - 1) * limit

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.name, p.name as profession, f.name as field,
               a.nationality, a.birth_year, COUNT(q.id) as quote_count
        FROM authors a
        LEFT JOIN professions p ON a.profession_id = p.id
        LEFT JOIN fields f ON a.field_id = f.id
        LEFT JOIN quotes q ON q.author_id = a.id
        GROUP BY a.id, a.name, p.name, f.name, a.nationality, a.birth_year
        HAVING COUNT(q.id) > 0
        ORDER BY quote_count DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route("/app/api/v1/quotes")
def app_quotes():
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 50)
    offset = (page - 1) * limit

    conn = get_db()
    cur = conn.cursor()

    where = []
    params = []

    keyword_group = request.args.get("keyword_group")
    if keyword_group:
        where.append("EXISTS (SELECT 1 FROM keywords k WHERE k.id = ANY(q.keyword_ids) AND k.group_name = %s)")
        params.append(keyword_group)

    keyword = request.args.get("keyword")
    if keyword:
        where.append("EXISTS (SELECT 1 FROM keywords k WHERE k.id = ANY(q.keyword_ids) AND k.name = %s)")
        params.append(keyword)

    situation = request.args.get("situation")
    if situation:
        where.append("EXISTS (SELECT 1 FROM situations s WHERE s.id = ANY(q.situation_ids) AND s.name = %s)")
        params.append(situation)

    situation_group = request.args.get("situation_group")
    if situation_group:
        where.append("EXISTS (SELECT 1 FROM situations s WHERE s.id = ANY(q.situation_ids) AND s.group_name = %s)")
        params.append(situation_group)

    author_id = request.args.get("author_id")
    if author_id:
        where.append("q.author_id = %s")
        params.append(author_id)

    where_clause = " AND ".join(where) if where else "1=1"
    params.extend([limit, offset])

    cur.execute(f"""
        SELECT q.id, q.text, q.text_original, q.source, q.impact_score,
               a.name as author_name, a.nationality,
               ARRAY(SELECT k.name FROM keywords k WHERE k.id = ANY(q.keyword_ids)) as keywords
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        WHERE q.status = 'published' AND {where_clause}
        ORDER BY COALESCE(q.impact_score, 3) DESC
        LIMIT %s OFFSET %s
    """, params)

    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(rows)


@app.route("/app/api/v1/quotes/<quote_id>")
def app_quote_detail(quote_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT q.id, q.text, q.text_original, q.original_language, q.source, q.year, q.impact_score,
               a.id as author_id, a.name as author_name, p.name as profession,
               f.name as field, a.nationality, a.birth_year,
               ARRAY(SELECT k.name FROM keywords k WHERE k.id = ANY(q.keyword_ids)) as keywords,
               ARRAY(SELECT s.name FROM situations s WHERE s.id = ANY(q.situation_ids)) as situations
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        LEFT JOIN professions p ON a.profession_id = p.id
        LEFT JOIN fields f ON a.field_id = f.id
        WHERE q.id = %s
    """, (quote_id,))
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({"error": "명언을 찾을 수 없습니다."}), 404

    d = dict(zip(cols, row))

    # 같은 저자의 다른 명언 3개
    cur.execute("""
        SELECT q.id, q.text, q.impact_score
        FROM quotes q WHERE q.author_id = %s AND q.id != %s
        ORDER BY COALESCE(q.impact_score, 3) DESC LIMIT 3
    """, (d["author_id"], quote_id))
    related = [{"id": r[0], "text": r[1], "impact_score": r[2]} for r in cur.fetchall()]

    cur.close(); conn.close()
    return jsonify({
        "id": d["id"], "text": d["text"], "text_original": d["text_original"],
        "original_language": d["original_language"], "source": d["source"],
        "year": d["year"], "impact_score": d["impact_score"],
        "keywords": d["keywords"] or [], "situations": d["situations"] or [],
        "author": {
            "id": d["author_id"], "name": d["author_name"], "profession": d["profession"],
            "field": d["field"], "nationality": d["nationality"], "birth_year": d["birth_year"],
        },
        "related_quotes": related,
    })


@app.route("/app/api/v1/quotes/batch", methods=["POST"])
def app_quotes_batch():
    data = request.get_json()
    ids = data.get("ids", [])[:50]
    if not ids:
        return jsonify([])

    conn = get_db()
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(ids))
    cur.execute(f"""
        SELECT q.id, q.text, q.text_original, q.source, q.impact_score,
               a.name as author_name, a.nationality,
               ARRAY(SELECT k.name FROM keywords k WHERE k.id = ANY(q.keyword_ids)) as keywords
        FROM quotes q
        JOIN authors a ON q.author_id = a.id
        WHERE q.status = 'published' AND q.id IN ({placeholders})
    """, ids)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)


# ===========================================================================
# Dashboard HTML
# ===========================================================================

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>매일 동기부여 대시보드</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;padding:24px}
h1{font-size:24px;margin-bottom:24px;color:#f8fafc}
h2{font-size:16px;margin-bottom:12px;color:#94a3b8;font-weight:500}
.stats{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}
.stat-card{background:#1e293b;border-radius:12px;padding:20px;flex:1;min-width:120px}
.stat-card .number{font-size:36px;font-weight:700;color:#38bdf8}
.stat-card .label{font-size:14px;color:#94a3b8;margin-top:4px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.card{background:#1e293b;border-radius:12px;padding:20px;max-height:500px;overflow-y:auto}
.bar{display:flex;align-items:center;margin-bottom:6px;font-size:13px}
.bar-label{width:120px;text-align:right;margin-right:10px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0}
.bar-fill{height:20px;border-radius:4px;transition:width 0.5s;min-width:2px}
.bar-count{margin-left:8px;color:#64748b;font-size:12px;white-space:nowrap}
.recent{margin-top:8px}
.recent-item{padding:12px 0;border-bottom:1px solid #334155}
.recent-item:last-child{border-bottom:none}
.recent-text{font-size:14px;line-height:1.5}
.recent-author{font-size:12px;color:#64748b;margin-top:4px}
.tag{display:inline-block;background:#334155;border-radius:4px;padding:2px 6px;font-size:11px;margin:2px;color:#94a3b8}
.gap-section{margin-top:8px}
.gap-item{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #334155;font-size:13px}
.gap-item .area{color:#94a3b8}
.gap-item .status{font-weight:600}
.status-low{color:#f87171}
.status-mid{color:#fbbf24}
.status-ok{color:#4ade80}
.section-title{font-size:18px;margin:32px 0 16px;color:#f8fafc;border-bottom:1px solid #334155;padding-bottom:8px}
</style>
</head>
<body>
<h1>매일 동기부여 대시보드</h1>

<div class="stats">
  <div class="stat-card"><div class="number" id="s-quotes">-</div><div class="label">총 명언</div></div>
  <div class="stat-card"><div class="number" id="s-authors">-</div><div class="label">총 저자</div></div>
  <div class="stat-card"><div class="number" id="s-relations">-</div><div class="label">저자 관계</div></div>
  <div class="stat-card"><div class="number" id="s-keywords">-</div><div class="label">키워드</div></div>
  <div class="stat-card"><div class="number" id="s-situations">-</div><div class="label">상황</div></div>
  <div class="stat-card"><div class="number" id="s-fields">-</div><div class="label">분야</div></div>
  <div class="stat-card"><div class="number" id="s-verified">-</div><div class="label">검증 완료</div></div>
</div>

<div class="grid">
  <div class="card"><h2>분야별 분포</h2><div id="by-field"></div></div>
  <div class="card"><h2>국가별 분포</h2><div id="by-nationality"></div></div>
  <div class="card"><h2>직업 그룹별</h2><div id="by-profession-group"></div></div>
  <div class="card"><h2>직업별 (개별)</h2><div id="by-profession"></div></div>
</div>

<div class="section-title">수집 갭 분석</div>
<div class="grid">
  <div class="card" style="grid-column:span 2"><div id="gap-analysis" class="gap-section"></div></div>
</div>

<div class="section-title">키워드</div>
<div class="grid">
  <div class="card"><h2>키워드 그룹별</h2><div id="by-keyword-group"></div></div>
  <div class="card"><h2>키워드 TOP 20 (개별)</h2><div id="by-keyword"></div></div>
</div>

<div class="section-title">상황</div>
<div class="grid">
  <div class="card"><h2>상황 그룹별</h2><div id="by-situation-group"></div></div>
  <div class="card"><h2>상황 TOP 15 (개별)</h2><div id="by-situation"></div></div>
</div>

<div class="section-title">트렌드 분석</div>
<div id="trends-time" style="font-size:12px;color:#64748b;margin-bottom:12px"></div>
<div class="grid">
  <div class="card"><h2>글로벌 트렌드</h2><div id="trends-global"></div></div>
  <div class="card"><h2>한국 트렌드</h2><div id="trends-korea"></div></div>
</div>

<div class="section-title">수집 이력</div>
<div class="grid">
  <div class="card" style="grid-column:span 2"><div id="collection-history"></div></div>
</div>

<div class="section-title">최근 수집</div>
<div class="grid">
  <div class="card" style="grid-column:span 2"><div id="recent" class="recent"></div></div>
</div>

<script>
const C={field:'#38bdf8',nat:'#818cf8',kw:'#a78bfa',kwg:'#f472b6',sit:'#fb923c',sitg:'#4ade80'};
const TARGET={
  field:{'철학':30,'문학':25,'과학':20,'정치':15,'역사':15,'예술':15,'종교':10,'경영':10,'스포츠':10,'심리학':10,'기술':10,'문화':10},
  nationality:{'KR':20,'US':20,'GB':15,'CN':15,'DE':10,'FR':10,'GR':10,'JP':10,'IN':10,'IT':10}
};

async function load(){
  const[stats,vstats,field,nat,prof,profg,kw,kwg,sit,sitg,history,recent]=await Promise.all([
    fetch('/api/stats').then(r=>r.json()),
    fetch('/api/verification-stats').then(r=>r.json()),
    fetch('/api/by-field').then(r=>r.json()),
    fetch('/api/by-nationality').then(r=>r.json()),
    fetch('/api/by-profession').then(r=>r.json()),
    fetch('/api/by-profession-group').then(r=>r.json()),
    fetch('/api/by-keyword').then(r=>r.json()),
    fetch('/api/by-keyword-group').then(r=>r.json()),
    fetch('/api/by-situation').then(r=>r.json()),
    fetch('/api/by-situation-group').then(r=>r.json()),
    fetch('/api/collection-history').then(r=>r.json()),
    fetch('/api/recent').then(r=>r.json()),
  ]);
  document.getElementById('s-quotes').textContent=stats.quotes;
  document.getElementById('s-authors').textContent=stats.authors;
  document.getElementById('s-relations').textContent=stats.author_relations;
  document.getElementById('s-keywords').textContent=stats.keywords;
  document.getElementById('s-situations').textContent=stats.situations;
  document.getElementById('s-fields').textContent=stats.fields;
  document.getElementById('s-verified').textContent=vstats.verified+'/'+stats.quotes;

  bars('by-field',field,'field',C.field);
  bars('by-nationality',nat,'nationality',C.nat);
  bars('by-profession',prof,'profession','#2dd4bf');
  bars('by-profession-group',profg,'group_name','#e879f9');
  bars('by-keyword',kw.slice(0,20),'keyword',C.kw);
  bars('by-keyword-group',kwg,'group_name',C.kwg);
  bars('by-situation',sit.slice(0,15),'situation',C.sit);
  bars('by-situation-group',sitg,'group_name',C.sitg);
  renderRecent(recent);
  renderGap(field,nat);
  renderHistory(history);
}

function bars(id,data,key,color){
  const el=document.getElementById(id);
  const max=data.length?Math.max(...data.map(d=>d.count)):1;
  el.innerHTML=data.map(d=>{
    const name=d[key]||'미분류';
    const pct=(d.count/max*100);
    const grp=d.group_name&&key!=='group_name'?' <span style="color:#475569;font-size:11px">('+d.group_name+')</span>':'';
    return '<div class="bar"><span class="bar-label" title="'+name+'">'+name+'</span><div class="bar-fill" style="width:'+pct+'%;background:'+color+'"></div><span class="bar-count">'+d.count+grp+'</span></div>';
  }).join('');
}

function renderRecent(data){
  document.getElementById('recent').innerHTML=data.map(d=>{
    const kws=(typeof d.keywords==='string'?JSON.parse(d.keywords):d.keywords)||[];
    return '<div class="recent-item"><div class="recent-text">\u201c'+d.text+'\u201d</div><div class="recent-author">\u2014 '+d.author+'</div><div>'+kws.map(k=>'<span class="tag">'+k+'</span>').join('')+'</div></div>';
  }).join('');
}

function renderGap(fieldData,natData){
  const el=document.getElementById('gap-analysis');
  let html='<div style="font-size:13px;color:#64748b;margin-bottom:12px">목표 대비 부족한 영역 (빨간색 우선 수집)</div>';
  const fMap={};fieldData.forEach(d=>fMap[d.field]=d.count);
  const nMap={};natData.forEach(d=>nMap[d.nationality]=d.count);
  const gaps=[];
  for(const[f,t]of Object.entries(TARGET.field)){const c=fMap[f]||0;gaps.push({area:f+' (분야)',current:c,target:t,pct:Math.round(c/t*100)})}
  for(const[n,t]of Object.entries(TARGET.nationality)){const c=nMap[n]||0;gaps.push({area:n+' (국가)',current:c,target:t,pct:Math.round(c/t*100)})}
  gaps.sort((a,b)=>a.pct-b.pct);
  html+=gaps.map(g=>{
    const cls=g.pct<30?'status-low':g.pct<70?'status-mid':'status-ok';
    return '<div class="gap-item"><span class="area">'+g.area+'</span><span class="status '+cls+'">'+g.current+'/'+g.target+' ('+g.pct+'%)</span></div>';
  }).join('');
  el.innerHTML=html;
}

async function loadTrends(){
  try{
    const res=await fetch('/api/trends');
    if(!res.ok){document.getElementById('trends-global').innerHTML='<span style="color:#64748b">데이터 없음</span>';document.getElementById('trends-korea').innerHTML='<span style="color:#64748b">데이터 없음</span>';return}
    const data=await res.json();
    if(data.fetched_at){document.getElementById('trends-time').textContent='마지막 조회: '+data.fetched_at}
    renderTrendBars('trends-global',data.global||{},'#38bdf8');
    renderTrendBars('trends-korea',data.korea||{},'#f472b6');
  }catch(e){console.error('트렌드 로드 실패',e)}
}

function renderTrendBars(id,obj,color){
  const el=document.getElementById(id);
  const entries=Object.entries(obj).sort((a,b)=>b[1]-a[1]);
  if(!entries.length){el.innerHTML='<span style="color:#64748b">데이터 없음</span>';return}
  const max=Math.max(...entries.map(e=>e[1]),1);
  el.innerHTML=entries.map(([k,v])=>{
    const pct=(v/max*100);
    return '<div class="bar"><span class="bar-label" title="'+k+'">'+k+'</span><div class="bar-fill" style="width:'+pct+'%;background:'+color+'"></div><span class="bar-count">'+v+'</span></div>';
  }).join('');
}

function renderHistory(data){
  const el=document.getElementById('collection-history');
  if(!data.length){el.innerHTML='<span style="color:#64748b">수집 이력이 없습니다.</span>';return}
  let html='<table style="width:100%;font-size:13px;border-collapse:collapse"><tr style="color:#64748b;border-bottom:1px solid #334155"><th style="text-align:left;padding:8px">일시</th><th>카테고리</th><th>요청</th><th>저장</th><th>중복</th><th>오류</th></tr>';
  html+=data.map(d=>'<tr style="border-bottom:1px solid #1e293b"><td style="padding:6px;color:#94a3b8">'+d.created_at.slice(0,16)+'</td><td style="text-align:center">'+d.category+'</td><td style="text-align:center">'+d.requested_count+'</td><td style="text-align:center;color:#4ade80">'+d.saved_count+'</td><td style="text-align:center;color:#fbbf24">'+d.duplicate_count+'</td><td style="text-align:center;color:#f87171">'+d.error_count+'</td></tr>').join('');
  html+='</table>';
  el.innerHTML=html;
}

load();
loadTrends();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("대시보드: http://localhost:5050")
    app.run(port=5050, debug=True)
