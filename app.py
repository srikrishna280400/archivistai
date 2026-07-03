import os
import json
import re
from datetime import datetime, timedelta
import pandas as pd
import requests
from flask import Flask, jsonify, request, render_template, send_from_directory, redirect

app = Flask(__name__, template_folder="templates")

DB_FILE = "articles_database.json"
EXCEL_FILE = "consolidated_categorized_articles.xlsx"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

TAGS = [
    "psychology",
    "music",
    "geopoltics/history",
    "inspiration",
    "tennis",
    "football",
    "cricket",
    "formula 1",
    "badminton",
    "cinema",
    "indian politics",
    "indian history",
    "tech/science",
    "interesting",
    "literature",
    "hp",
    "startup stories",
    "financial markets",
    "misanthropy",
    "startup vcs/sales",
    "health"
]

def is_supabase_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def delete_expired_from_supabase(art_id):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles?id=eq.{art_id}"
        try:
            requests.delete(url, headers=get_supabase_headers(), timeout=5)
        except Exception as e:
            print(f"Error deleting expired article {art_id} from Supabase: {e}")

def load_db():
    if is_supabase_enabled():
        try:
            url = f"{SUPABASE_URL}/rest/v1/articles?order=id.asc"
            res = requests.get(url, headers=get_supabase_headers(), timeout=10)
            if res.status_code == 200:
                articles = res.json()
                # Run auto-cleanup of trash older than 15 days
                cleaned_articles, changed = clean_expired_trash(articles)
                if changed:
                    for a in articles:
                        if a not in cleaned_articles:
                            delete_expired_from_supabase(a["id"])
                return cleaned_articles
        except Exception as e:
            print(f"Supabase fetch failed, falling back to local database: {e}")

    # Fallback to local
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    # Auto-cleanup of trash older than 15 days
    cleaned_articles, changed = clean_expired_trash(articles)
    if changed:
        save_db_no_sync(cleaned_articles)
        return cleaned_articles
    return articles

def clean_expired_trash(articles):
    now = datetime.utcnow()
    changed = False
    cleaned_articles = []
    for a in articles:
        deleted_at = a.get("deleted_at")
        if deleted_at:
            try:
                del_dt = datetime.fromisoformat(deleted_at)
                if now - del_dt > timedelta(days=15):
                    changed = True
                    continue  # Permanently deleted
            except Exception:
                pass
        cleaned_articles.append(a)
    return cleaned_articles, changed

def save_db_no_sync(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_db(data):
    save_db_no_sync(data)
    # Sync non-deleted to Excel
    non_deleted = [a for a in data if not a.get("deleted_at")]
    sync_to_excel(non_deleted)

def sync_to_excel(articles):
    rows = []
    for a in articles:
        headline = a['original_title']
        if a.get('crawl_status') == 'success':
            if a.get('crawled_h1'):
                headline = a['crawled_h1']
            elif a.get('crawled_title'):
                headline = a['crawled_title']
                
        rows.append({
            "ID": a['id'],
            "Source": a['original_source'],
            "Original Title": a['original_title'],
            "Web Headline/Topic": headline,
            "URL": a['url'],
            "Timestamp": a['timestamp'],
            "Crawl Status": a['crawl_status'],
            "Tag": a.get('assigned_tag') if a.get('assigned_tag') else "interesting"
        })
    df = pd.DataFrame(rows)
    df.to_excel(EXCEL_FILE, index=False)

def update_supabase_article(art_id, payload):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles?id=eq.{art_id}"
        try:
            res = requests.patch(url, headers=get_supabase_headers(), json=payload, timeout=5)
            return res.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Error updating Supabase article {art_id}: {e}")
    return False

def delete_supabase_article(art_id):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles?id=eq.{art_id}"
        try:
            res = requests.delete(url, headers=get_supabase_headers(), timeout=5)
            return res.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Error deleting Supabase article {art_id}: {e}")
    return False

def insert_supabase_article(payload):
    if is_supabase_enabled():
        url = f"{SUPABASE_URL}/rest/v1/articles"
        try:
            res = requests.post(url, headers=get_supabase_headers(), json=payload, timeout=5)
            return res.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Error inserting Supabase article: {e}")
    return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/android")
def android_index():
    return render_template("index-android.html")

@app.route("/manifest-android.json")
def serve_android_manifest():
    root_manifest_path = os.path.join(app.root_path, "templates", "manifest.json")
    try:
        with open(root_manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        manifest_data["start_url"] = "/android"
        return jsonify(manifest_data)
    except Exception:
        return send_from_directory("templates", "manifest.json", mimetype="application/json")

# Serve PWA manifest and service worker from the root for strict scoping
@app.route("/manifest.json")
def serve_manifest():
    return send_from_directory("templates", "manifest.json", mimetype="application/json")

@app.route("/service-worker.js")
def serve_sw():
    return send_from_directory("templates", "service-worker.js", mimetype="application/javascript")

@app.route("/icons/<path:filename>")
def serve_icons(filename):
    return send_from_directory("templates/icons", filename)

@app.route("/api/articles", methods=["GET"])
def get_articles():
    articles = load_db()
    return jsonify(articles)

@app.route("/api/tags", methods=["GET"])
def get_tags():
    return jsonify(TAGS)

@app.route("/api/articles/<int:art_id>/tag", methods=["POST"])
def update_tag(art_id):
    req_data = request.get_json()
    if not req_data or "tag" not in req_data:
        return jsonify({"error": "Missing tag field"}), 400
        
    new_tag = req_data["tag"].strip().lower()
    if new_tag and new_tag not in TAGS:
        return jsonify({"error": f"Invalid tag. Must be one of {TAGS}"}), 400
        
    if is_supabase_enabled():
        if update_supabase_article(art_id, {"assigned_tag": new_tag if new_tag else None}):
            return jsonify({"success": True, "message": f"Updated article {art_id} tag to '{new_tag}'"})
        return jsonify({"error": "Failed to update tag in Supabase"}), 500

    articles = load_db()
    found = False
    for a in articles:
        if a["id"] == art_id:
            a["assigned_tag"] = new_tag if new_tag else None
            found = True
            break
            
    if not found:
        return jsonify({"error": "Article not found"}), 404
        
    save_db(articles)
    return jsonify({"success": True, "message": f"Updated article {art_id} tag to '{new_tag}'"})

@app.route("/api/articles/<int:art_id>/trash", methods=["POST"])
def trash_article(art_id):
    deleted_time = datetime.utcnow().isoformat()
    if is_supabase_enabled():
        if update_supabase_article(art_id, {"deleted_at": deleted_time}):
            return jsonify({"success": True, "message": f"Article {art_id} moved to Trash bin"})
        return jsonify({"error": "Failed to move article to Trash in Supabase"}), 500

    articles = load_db()
    found = False
    for a in articles:
        if a["id"] == art_id:
            a["deleted_at"] = deleted_time
            found = True
            break
    if not found:
        return jsonify({"error": "Article not found"}), 404
    save_db(articles)
    return jsonify({"success": True, "message": f"Article {art_id} moved to Trash bin"})

@app.route("/api/articles/<int:art_id>/restore", methods=["POST"])
def restore_article(art_id):
    if is_supabase_enabled():
        if update_supabase_article(art_id, {"deleted_at": None}):
            return jsonify({"success": True, "message": f"Article {art_id} restored from Trash bin"})
        return jsonify({"error": "Failed to restore article in Supabase"}), 500

    articles = load_db()
    found = False
    for a in articles:
        if a["id"] == art_id:
            a["deleted_at"] = None
            found = True
            break
    if not found:
        return jsonify({"error": "Article not found"}), 404
    save_db(articles)
    return jsonify({"success": True, "message": f"Article {art_id} restored from Trash bin"})

@app.route("/api/articles/<int:art_id>/delete", methods=["DELETE"])
def delete_permanent(art_id):
    if is_supabase_enabled():
        if delete_supabase_article(art_id):
            return jsonify({"success": True, "message": f"Article {art_id} permanently deleted"})
        return jsonify({"error": "Failed to delete article in Supabase"}), 500

    articles = load_db()
    filtered = [a for a in articles if a["id"] != art_id]
    if len(filtered) == len(articles):
        return jsonify({"error": "Article not found"}), 404
    save_db(filtered)
    return jsonify({"success": True, "message": f"Article {art_id} permanently deleted"})

@app.route("/api/share", methods=["GET", "POST"])
def share_target():
    url = request.args.get("url") or request.form.get("url")
    title = request.args.get("title") or request.form.get("title")
    text = request.args.get("text") or request.form.get("text")
    
    # Clean and parse URL from text if needed (mobile shares often pack text and URL together)
    if not url and text:
        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            url = urls[0]
            
    if not url:
        return redirect("/?error=no_url")
        
    articles = load_db()
    next_id = max([a["id"] for a in articles]) + 1 if articles else 1
    
    new_article = {
        "id": next_id,
        "original_source": "shared",
        "original_title": title or "Shared Link",
        "crawled_title": title or "Shared Link",
        "crawled_h1": "",
        "url": url,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "crawl_status": "pending",
        "assigned_tag": None,  # Shared links start as untagged
        "deleted_at": None
    }
    
    if is_supabase_enabled():
        if insert_supabase_article(new_article):
            return redirect("/")
        return redirect("/?error=supabase_save_failed")
        
    articles.append(new_article)
    save_db(articles)
    
    # Successfully added! Redirect to home page
    return redirect("/")

@app.route("/api/stats", methods=["GET"])
def get_stats():
    articles = load_db()
    non_deleted = [a for a in articles if not a.get("deleted_at")]
    total = len(non_deleted)
    
    tag_counts = {t: 0 for t in TAGS}
    crawl_counts = {"success": 0, "pending": 0, "failed": 0}
    source_counts = {"pocket": 0, "instapaper": 0, "shared": 0}
    
    for a in non_deleted:
        # Source
        source = a.get("original_source", "pocket")
        source_counts[source] = source_counts.get(source, 0) + 1
        
        # Crawl Status
        status = a.get("crawl_status", "pending")
        if "success" in status:
            crawl_counts["success"] += 1
        elif "pending" in status:
            crawl_counts["pending"] += 1
        else:
            crawl_counts["failed"] += 1
            
        # Tag
        tag = a.get("assigned_tag")
        if tag in tag_counts:
            tag_counts[tag] += 1
        elif tag is None:
            # Untagged
            pass
        else:
            # Fallback
            tag_counts["interesting"] = tag_counts.get("interesting", 0) + 1
            
    return jsonify({
        "total_articles": total,
        "tag_counts": tag_counts,
        "crawl_counts": crawl_counts,
        "source_counts": source_counts,
        "total_trash": len(articles) - total
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
