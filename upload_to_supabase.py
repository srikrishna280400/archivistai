import os
import json
import requests

DB_FILE = "articles_database.json"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set!")
        print("Please export them or run this script with them set. For example:")
        print("SUPABASE_URL=https://xyz.supabase.co SUPABASE_KEY=your_anon_key python upload_to_supabase.py")
        return

    if not os.path.exists(DB_FILE):
        print(f"❌ Error: Local database file {DB_FILE} not found!")
        return

    print("📖 Reading local articles database...")
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f"✅ Loaded {len(articles)} articles locally.")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # Upsert matching IDs
    }

    # Upload in chunks of 100 to avoid any HTTP payload/timeout limits
    chunk_size = 100
    total = len(articles)

    print("🚀 Bulk uploading articles to Supabase in chunks...")
    for i in range(0, total, chunk_size):
        chunk = articles[i:i + chunk_size]
        
        # Clean null values if needed (empty strings map to NULL in SQL)
        for item in chunk:
            if "assigned_tag" in item and item["assigned_tag"] == "":
                item["assigned_tag"] = None
            if "deleted_at" in item and item["deleted_at"] == "":
                item["deleted_at"] = None

        url = f"{SUPABASE_URL}/rest/v1/articles"
        try:
            res = requests.post(url, headers=headers, json=chunk, timeout=15)
            if res.status_code in [200, 201, 204]:
                print(f"🔹 Uploaded articles {i+1} to {min(i+chunk_size, total)} of {total}")
            else:
                print(f"❌ Failed to upload chunk starting at index {i}: Status {res.status_code}")
                print(res.text)
                return
        except Exception as e:
            print(f"❌ Network connection error: {e}")
            return

    print("\n🎉 Success! Your Supabase database is fully seeded with your local articles.")

if __name__ == "__main__":
    main()
