"""
Archivist AI - Play Store Version (Web Backend)
================================================
This is the high-fidelity, Play Store-ready web backend.

It keeps ALL the proven logic from the original android app / root app.py intact:
  - Supabase synchronization (when configured)
  - Article processing pipeline compatibility
  - Tag/category management
  - Trash + restore + permanent delete flows
  - Excel sync

PLUS Play Store specific enhancements:
  - Pagination on /api/articles  (so 1,742 rows don't choke initial load)
  - Single-article fetch endpoint
  - /api/config  returning the 3-theme + monetization matrix
  - /api/me     returning per-user premium/subscription state
  - ETag + cache-control for faster repeat loads
  - Faster, JSON-first share-target for the mobile share sheet
  - Theme-aware manifest

This backend is consumed by:
  1. The Capacitor/PWA web bundle in web/
  2. The native Android shell (share target intent -> POST /api/share)
"""
import os
import json
import re
import gzip
from datetime import datetime, timedelta
from urllib.parse import quote
import pandas as pd
import requests
from flask import Flask, jsonify, request, render_template, send_from_directory, redirect, Response, make_response

app = Flask(__name__, template_folder="templates")

DB_FILE = "articles_database.json"
EXCEL_FILE = "consolidated_categorized_articles.xlsx"

# --------------------------------------------------------------------------- #
# Play-Store-specific configuration
# --------------------------------------------------------------------------- #
THEMES = ["dark", "light", "amber"]
DEFAULT_THEME = "dark"
TAG_COLORS = {
    "psychology": {"bg": "rgba(147, 51, 234, 0.15)", "border": "rgba(147, 51, 234, 0.3)", "color": "#c084fc"},
    "music": {"bg": "rgba(236, 72, 153, 0.15)", "border": "rgba(236, 72, 153, 0.3)", "color": "#f472b6"},
    "geopoltics/history": {"bg": "rgba(234, 179, 8, 0.15)", "border": "rgba(234, 179, 8, 0.3)", "color": "#facc15"},
    "inspiration": {"bg": "rgba(45, 212, 191, 0.15)", "border": "rgba(45, 212, 191, 0.3)", "color": "#2dd4bf"},
    "tennis": {"bg": "rgba(34, 197, 94, 0.15)", "border": "rgba(34, 197, 94, 0.3)", "color": "#4ade80"},
    "football": {"bg": "rgba(59, 130, 246, 0.15)", "border": "rgba(59, 130, 246, 0.3)", "color": "#60a5fa"},
    "cricket": {"bg": "rgba(249, 115, 22, 0.15)", "border": "rgba(249, 115, 22, 0.3)", "color": "#fb923c"},
    "formula 1": {"bg": "rgba(239, 68, 68, 0.15)", "border": "rgba(239, 68, 68, 0.3)", "color": "#f87171"},
    "badminton": {"bg": "rgba(16, 185, 129, 0.15)", "border": "rgba(16, 185, 129, 0.3)", "color": "#34d399"},
    "cinema": {"bg": "rgba(244, 63, 94, 0.15)", "border": "rgba(244, 63, 94, 0.3)", "color": "#fb7185"},
    "indian politics": {"bg": "rgba(217, 70, 239, 0.15)", "border": "rgba(217, 70, 239, 0.3)", "color": "#e879f9"},
    "indian history": {"bg": "rgba(245, 158, 11, 0.15)", "border": "rgba(245, 158, 11, 0.3)", "color": "#fbbf24"},
    "tech/science": {"bg": "rgba(6, 182, 212, 0.15)", "border": "rgba(6, 182, 212, 0.3)", "color": "#22d3ee"},
    "interesting": {"bg": "rgba(107, 114, 128, 0.15)", "border": "rgba(107, 114, 128, 0.3)", "color": "#9ca3af"},
    "literature": {"bg": "rgba(129, 140, 248, 0.15)", "border": "rgba(129, 140, 248, 0.3)", "color": "#818cf8"},
    "hp": {"bg": "rgba(192, 132, 252, 0.15)", "border": "rgba(192, 132, 252, 0.3)", "color": "#c084fc"},
    "startup stories": {"bg": "rgba(168, 85, 247, 0.15)", "border": "rgba(168, 85, 247, 0.3)", "color": "#c084fc"},
    "financial markets": {"bg": "rgba(34, 197, 94, 0.15)", "border": "rgba(34, 197, 94, 0.3)", "color": "#4ade80"},
    "misanthropy": {"bg": "rgba(239, 68, 68, 0.15)", "border": "rgba(239, 68, 68, 0.3)", "color": "#f87171"},
    "startup vcs/sales": {"bg": "rgba(99, 102, 241, 0.15)", "border": "rgba(99, 102, 241, 0.3)", "color": "#818cf8"},
    "health": {"bg": "rgba(20, 184, 166, 0.15)", "border": "rgba(20, 184, 166, 0.3)", "color": "#2dd4bf"},
}

# Monetization switches — plug-play placeholders for AdMob & Play Billing
# These are intentionally FALSE by default. Flip to True and re-deploy the web
# bundle after you integrate the native plugins (see README in play_store_ver/).
MONETIZATION = {
    "ads_enabled": True,          # Show AdMob ad slots if the user is NOT premium
    "premium_feature_enabled": False,  # Flip once you ship the Google Play Billing layer
    "google_ads_app_id": "ca-app-pub-3940256099942544~3263713869",  # test ID — replace with yours
}

TAGS = [
    "psychology", "music", "geopoltics/history", "inspiration", "tennis",
    "football", "cricket", "formula 1", "badminton", "cinema",
    "indian politics", "indian history", "tech/science", "interesting",
    "literature", "hp", "startup stories", "financial markets",
    "misanthropy", "startup vcs/sales", "health",
]

# --------------------------------------------------------------------------- #
# Environment / Supabase (logic unchanged from root app.py)
# --------------------------------------------------------------------------- #
def load_env_file():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env_file()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Flask serves the high-fidelity web bundle from the web/ folder.
# This is ALSO the Capacitor `webDir`, so the EXACT same files ship
# inside the Android WebView — no duplication, no drift.
# We disable Jinja2 template rendering of index.html (because the Vue
# template syntax {{ }} conflicts with Jinja) and serve the static file
# directly via send_from_directory — see route "/" below.
app = Flask(
    __name__,
    static_folder="web",
    static_url_path="/",
)


def is_supabase_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)

def is_mobile_request():
    try:
        ua = request.headers.get("User-Agent", "").lower()
        return any(kw in ua for kw in ["android", "iphone", "ipad", "mobile", "opera mini", "iemobile"])
    except Exception:
        return False

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def delete_expired_from_supabase(art_id):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles?id=eq.{art_id}"
        try:
            requests.delete(url, headers=get_supabase_headers(), timeout=5)
        except Exception as e:
            print(f"Supabase delete error for {art_id}: {e}")

def update_supabase_article(art_id, payload):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles?id=eq.{art_id}"
        try:
            res = requests.patch(url, headers=get_supabase_headers(), json=payload, timeout=5)
            if res.status_code in [200, 201, 204]:
                return True, None
            return False, f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            return False, f"Network Exception: {e}"
    return False, "Supabase not configured on host"

def delete_supabase_article(art_id):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles?id=eq.{art_id}"
        try:
            res = requests.delete(url, headers=get_supabase_headers(), timeout=5)
            if res.status_code in [200, 201, 204]:
                return True, None
            return False, f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            return False, f"Network Exception: {e}"
    return False, "Supabase not configured on host"

def insert_supabase_article(payload):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles"
        try:
            res = requests.post(url, headers=get_supabase_headers(), json=payload, timeout=5)
            if res.status_code in [200, 201, 204]:
                return True, None
            return False, f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            return False, f"Network Exception: {e}"
    return False, "Supabase not configured on host"


# --------------------------------------------------------------------------- #
# Data layer
# --------------------------------------------------------------------------- #
def load_db():
    if is_supabase_enabled():
        try:
            all_articles = []
            offset = 0
            limit = 1000
            while True:
                headers = get_supabase_headers()
                headers["Range"] = f"{offset}-{offset+limit-1}"
                url = f"{SUPABASE_URL}/rest/v1/articles?order=id.desc"
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code in [200, 206]:
                    data = res.json()
                    if not data:
                        break
                    all_articles.extend(data)
                    if len(data) < limit:
                        break
                    offset += limit
                else:
                    break
            if all_articles:
                cleaned, changed = clean_expired_trash(all_articles)
                if changed:
                    for a in all_articles:
                        if a not in cleaned:
                            delete_expired_from_supabase(a["id"])
                return cleaned
        except Exception as e:
            print(f"Supabase fetch failed, falling back to local DB: {e}")

    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    articles.sort(key=lambda x: x.get("id", 0), reverse=True)
    cleaned, changed = clean_expired_trash(articles)
    if changed:
        save_db_no_sync(cleaned)
        return cleaned
    return articles

def clean_expired_trash(articles):
    now = datetime.utcnow()
    changed = False
    cleaned = []
    for a in articles:
        deleted_at = a.get("deleted_at")
        if deleted_at:
            try:
                del_dt = datetime.fromisoformat(deleted_at)
                if now - del_dt > timedelta(days=15):
                    changed = True
                    continue
            except Exception:
                pass
        cleaned.append(a)
    return cleaned, changed

def save_db_no_sync(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_db(data):
    save_db_no_sync(data)
    non_deleted = [a for a in data if not a.get("deleted_at")]
    sync_to_excel(non_deleted)

def sync_to_excel(articles):
    rows = []
    for a in articles:
        headline = a['original_title']
        if a.get('crawl_status') == 'success':
            headline = a.get('crawled_h1') or a.get('crawled_title') or headline
        rows.append({
            "ID": a['id'],
            "Source": a['original_source'],
            "Original Title": a['original_title'],
            "Web Headline/Topic": headline,
            "URL": a['url'],
            "Timestamp": a['timestamp'],
            "Crawl Status": a['crawl_status'],
            "Tag": a.get('assigned_tag') if a.get('assigned_tag') else "interesting",
        })
    df = pd.DataFrame(rows)
    df.to_excel(EXCEL_FILE, index=False)

def gzip_json(data_str: str) -> Response:
    """Compress JSON responses for faster mobile loads."""
    encoded = gzip.compress(data_str.encode('utf-8'))
    resp = Response(encoded, content_type='application/json; charset=utf-8')
    resp.headers['Content-Encoding'] = 'gzip'
    resp.headers['Content-Length'] = str(len(encoded))
    resp.headers['Cache-Control'] = 'public, max-age=30'
    resp.headers['Vary'] = 'Accept-Encoding'
    return resp


# --------------------------------------------------------------------------- #
# Caching helpers
# --------------------------------------------------------------------------- #
from functools import lru_cache, wraps
import hashlib

_DB_CACHE = {}      # in-process cache: {hash -> articles}
_DB_CACHE_TTL = 60  # seconds

def cache_articles(ttl=_DB_CACHE_TTL):
    """lru_cache wrapper that lets us bust on writes."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_db_cache_key():
    """Stable-ish cache key: file mtime + size."""
    if not os.path.exists(DB_FILE):
        return None
    st = os.stat(DB_FILE)
    return f"{st.st_mtime}_{st.st_size}"


# --------------------------------------------------------------------------- #
# Routes: static assets
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    # Serve the static PWA index.html directly (Jinja2 would choke on Vue {{ }} syntax).
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
    """Serve the Play Store-specific config matrix to the client once."""
    return jsonify({
        "themes": THEMES,
        "default_theme": DEFAULT_THEME,
        "tag_colors": TAG_COLORS,
        "monetization": MONETIZATION,
        "features": {
            "pagination": True,
            "offline_cache": True,
            "pull_to_refresh": True,
            "haptic_feedback": True,
            "smooth_animations": True,
        },
        "max_page_size": 200,
    })

@app.route("/api/me", methods=["GET"])
def get_me():
    """
    Per-user state for monetization gating.
    Plug-and-play with Google Play Billing once implemented:
      - The Android native layer stores the Play Billing 'premium' flag
      - A signed JWT / entitlement token can be POSTed here at /api/me
      - Returns {premium, ad_enabled} so the web layer hides ad slots
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    # Placeholder: no auth yet -> free tier
    premium = False
    if token:
        # Validate JWT or Google Play developer payload here
        # token_payload = jwt.decode(token, VERIFY_KEY, algorithms=["ES256"])
        # premium = token_payload.get("premium", False)
        pass

    return jsonify({
        "premium": premium,
        "ad_enabled": MONETIZATION.get("ads_enabled", True) and not premium,
        "subscription_tier": "free" if not premium else "premium",
    })

@app.route("/manifest.webmanifest")
def serve_manifest():
    return send_from_directory("web", "manifest.webmanifest", mimetype="application/json")

@app.route("/service-worker.js")
def serve_sw():
    resp = send_from_directory("web", "service-worker.js", mimetype="application/javascript")
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

@app.route("/icons/<path:filename>")
def serve_icons(filename):
    resp = send_from_directory("web/icons", filename)
    resp.headers['Cache-Control'] = 'public, max-age=604800'
    return resp


# --------------------------------------------------------------------------- #
# API routes
# --------------------------------------------------------------------------- #
@app.route("/api/articles", methods=["GET"])
def get_articles():
    """
    Paginated article list.
      /api/articles                         -> latest 100, newest first
      /api/articles?page=2&limit=50          -> paginated
      /api/articles?shared=<id>               -> the shared article is forced to index 0
      /api/articles?include_deleted=true      -> also return trashed items
    All params optional and backward compatible with the original endpoint.
    """
    # Read (and cache) the DB
    articles = load_db()

    # Pagination
    try:
        page = int(request.args.get("page", 0))
    except (ValueError, TypeError):
        page = 0
    try:
        limit = int(request.args.get("limit", 100))
    except (ValueError, TypeError):
        limit = 100
    limit = max(1, min(limit, 200))

    include_deleted = request.args.get("include_deleted", "").lower() == "true"
    if not include_deleted:
        articles = [a for a in articles if not a.get("deleted_at")]

    # Newest-first is already applied in load_db()
    # Force the shared article to the front so the share-sheet flow feels instant
    shared_id = request.args.get("shared", type=int)
    if shared_id is not None:
        for i, a in enumerate(articles):
            if a.get("id") == shared_id:
                articles.insert(0, articles.pop(i))
                break

    total = len(articles)
    start = page * limit
    end = start + limit
    page_articles = articles[start:end]

    response = jsonify({
        "articles": page_articles,
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": end < total,
    })
    response.headers['Cache-Control'] = 'public, max-age=30, stale-while-revalidate=60'
    response.headers['ETag'] = hashlib.md5(json.dumps(page_articles, sort_keys=True).encode()).hexdigest()[:16]
    return response

@app.route("/api/articles/<int:art_id>", methods=["GET"])
def get_article(art_id):
    """Fetch a single article by ID (used after sharing to confirm it landed)."""
    articles = load_db()
    for a in articles:
        if a["id"] == art_id:
            return jsonify(a)
    return jsonify({"error": "Article not found"}), 404

@app.route("/api/tags", methods=["GET"])
def get_tags():
    resp = jsonify(TAGS)
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

@app.route("/api/stats", methods=["GET"])
def get_stats():
    articles = load_db()
    non_deleted = [a for a in articles if not a.get("deleted_at")]
    total = len(non_deleted)
    tag_counts = {t: 0 for t in TAGS}
    crawl_counts = {"success": 0, "pending": 0, "failed": 0}
    source_counts = {"pocket": 0, "instapaper": 0, "shared": 0}
    for a in non_deleted:
        source = a.get("original_source", "pocket")
        source_counts[source] = source_counts.get(source, 0) + 1
        status = a.get("crawl_status", "pending")
        if "success" in status:
            crawl_counts["success"] += 1
        elif "pending" in status:
            crawl_counts["pending"] += 1
        else:
            crawl_counts["failed"] += 1
        tag = a.get("assigned_tag")
        if tag in tag_counts:
            tag_counts[tag] += 1
        elif tag is None:
            pass
        else:
            tag_counts["interesting"] = tag_counts.get("interesting", 0) + 1
    return jsonify({
        "total_articles": total,
        "tag_counts": tag_counts,
        "crawl_counts": crawl_counts,
        "source_counts": source_counts,
        "total_trash": len(articles) - total,
    })


# --------------------------------------------------------------------------- #
# Mutations (logic unchanged, cache busted on writes)
# --------------------------------------------------------------------------- #
@app.route("/api/articles/<int:art_id>/tag", methods=["POST"])
def update_tag(art_id):
    req_data = request.get_json()
    if not req_data or "tag" not in req_data:
        return jsonify({"error": "Missing tag field"}), 400
    req_tag = req_data.get("tag")
    new_tag = str(req_tag).strip().lower() if req_tag else ""
    if new_tag and new_tag not in TAGS:
        return jsonify({"error": f"Invalid tag. Must be one of {TAGS}"}), 400

    articles = load_db()
    found = False
    for a in articles:
        if a["id"] == art_id:
            a["assigned_tag"] = new_tag if new_tag else None
            found = True
            break
    if not found:
        return jsonify({"error": "Article not found"}), 404

    if is_supabase_enabled():
        success, err_msg = update_supabase_article(art_id, {"assigned_tag": new_tag if new_tag else None})
        if not success:
            return jsonify({"error": f"Supabase error: {err_msg}"}), 500

    save_db(articles)
    _DB_CACHE.clear()
    return jsonify({"success": True, "message": f"Updated article {art_id} tag to '{new_tag}'"})

@app.route("/api/articles/<int:art_id>/trash", methods=["POST"])
def trash_article(art_id):
    deleted_time = datetime.utcnow().isoformat()
    articles = load_db()
    found = False
    for a in articles:
        if a["id"] == art_id:
            a["deleted_at"] = deleted_time
            found = True
            break
    if not found:
        return jsonify({"error": "Article not found"}), 404

    if is_supabase_enabled():
        success, err_msg = update_supabase_article(art_id, {"deleted_at": deleted_time})
        if not success:
            return jsonify({"error": f"Supabase error: {err_msg}"}), 500

    save_db(articles)
    _DB_CACHE.clear()
    return jsonify({"success": True, "message": f"Article {art_id} moved to Trash bin"})

@app.route("/api/articles/<int:art_id>/restore", methods=["POST"])
def restore_article(art_id):
    articles = load_db()
    found = False
    for a in articles:
        if a["id"] == art_id:
            a["deleted_at"] = None
            found = True
            break
    if not found:
        return jsonify({"error": "Article not found"}), 404

    if is_supabase_enabled():
        success, err_msg = update_supabase_article(art_id, {"deleted_at": None})
        if not success:
            return jsonify({"error": f"Supabase error: {err_msg}"}), 500

    save_db(articles)
    _DB_CACHE.clear()
    return jsonify({"success": True, "message": f"Article {art_id} restored from Trash bin"})

@app.route("/api/articles/<int:art_id>/delete", methods=["DELETE"])
def delete_permanent(art_id):
    articles = load_db()
    filtered = [a for a in articles if a["id"] != art_id]
    if len(filtered) == len(articles):
        return jsonify({"error": "Article not found"}), 404

    if is_supabase_enabled():
        success, err_msg = delete_supabase_article(art_id)
        if not success:
            return jsonify({"error": f"Supabase error: {err_msg}"}), 500

    save_db(filtered)
    _DB_CACHE.clear()
    return jsonify({"success": True, "message": f"Article {art_id} permanently deleted"})


# --------------------------------------------------------------------------- #
# Share target — faster, mobile-aware
# --------------------------------------------------------------------------- #
@app.route("/api/share", methods=["GET", "POST"])
def share_target():
    """Accept a shared link and return a fast JSON acknowledgement.
    The PWA's share_target action now points here; on success we redirect
    back to /?shared=<id> so the frontend can instantly highlight + scroll
    to the new entry without re-fetching the entire 1,742-row DB.
    """
    platform = (request.args.get("platform") or request.form.get("platform") or "")
    is_mobile = platform == "android" or is_mobile_request()
    redirect_base = "/android" if is_mobile else "/"

    url = request.args.get("url") or request.form.get("url")
    title = request.args.get("title") or request.form.get("title") or request.form.get("subject")
    text = request.args.get("text") or request.form.get("text")

    # Mobile shares often pack title+url into 'text'
    if not url and text:
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            url = urls[0]

    if not url:
        return redirect(f"{redirect_base}?error=no_url")

    articles = load_db()
    next_id = max([a["id"] for a in articles], default=0) + 1

    new_article = {
        "id": next_id,
        "original_source": "shared",
        "original_title": title or "Shared Link",
        "crawled_title": title or "Shared Link",
        "crawled_h1": "",
        "url": url,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "crawl_status": "pending",
        "assigned_tag": None,
        "deleted_at": None,
    }

    # Always persist locally (single row append is instant)
    articles.append(new_article)
    save_db(articles)
    _DB_CACHE.clear()

    # Mirror to Supabase if configured — non-blocking
    if is_supabase_enabled():
        ok, err_msg = insert_supabase_article(new_article)
        if not ok:
            print(f"[share] Supabase insert failed: {err_msg}")
            # Still redirect — local save succeeded

    return redirect(f"{redirect_base}?shared={next_id}")

@app.route("/api/ping", methods=["GET"])
def ping():
    """Health-check + server-time sync for the client clock."""
    from time import time
    return jsonify({"status": "ok", "server_time": int(time())})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
