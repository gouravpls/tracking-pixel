import os, sqlite3, json, datetime
from flask import Flask, request, Response

app = Flask(__name__)

# ---- 1x1 transparent PNG (valid PNG bytes) ----
PNG_1X1_TRANSPARENT = bytes([
    137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82,
    0,0,0,1,0,0,0,1,8,6,0,0,0,31,21,196,137,0,0,
    0,10,73,68,65,84,120,156,99,96,0,0,0,2,0,1,
    229,39,212,162,0,0,0,0,73,69,78,68,174,66,96,130
])

DB_PATH = os.environ.get("PIXEL_DB", "opens.db")

def _ensure_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS opens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            rid TEXT,
            mid TEXT,
            ua TEXT,
            ip TEXT,
            country TEXT,
            referer TEXT
        )
    """)
    conn.commit()
    conn.close()

_ensure_db()

def _log_open(rid, mid, ua, ip, country, referer):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO opens (ts, rid, mid, ua, ip, country, referer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.datetime.utcnow().isoformat()+"Z", rid, mid, ua, ip, country, referer))
    conn.commit()
    conn.close()

@app.route("/pixel.png")
def pixel():
    # Identify the message & recipient (you set these in the URL)
    rid = request.args.get("rid", "unknown")    # recipient identifier
    mid = request.args.get("mid", "")           # message id/slug

    # What we can observe
    ua = request.headers.get("User-Agent")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    country = request.headers.get("CF-IPCountry")  # present on some hosts/CDNs
    referer = request.headers.get("Referer")

    _log_open(rid, mid, ua, ip, country, referer)

    # Serve a non-cached 1x1 transparent PNG
    headers = {
        "Content-Type": "image/png",
        "Content-Length": str(len(PNG_1X1_TRANSPARENT)),
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Robots-Tag": "noindex, nofollow"
    }
    return Response(PNG_1X1_TRANSPARENT, headers=headers)

@app.route("/stats")
def stats():
    """Quick JSON dump of recent opens (for testing)."""
    limit = int(request.args.get("limit", "50"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ts, rid, mid, ip, substr(ua,1,140), referer FROM opens ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    out = [
        {"ts": r[0], "rid": r[1], "mid": r[2], "ip": r[3], "ua": r[4], "referer": r[5]}
        for r in rows
    ]
    return Response(json.dumps(out, indent=2), mimetype="application/json")

if __name__ == "__main__":
    # Local dev
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
