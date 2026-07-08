import os
import json
import requests
import pandas as pd

DB_FILE = "articles_database.json"
EXCEL_FILE = "consolidated_categorized_articles.xlsx"

def load_env_file():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Load credentials from .env
load_env_file()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def sync_to_excel(articles):
    rows = []
    for a in articles:
        headline = a.get('original_title', '')
        if a.get('crawl_status') == 'success':
            if a.get('crawled_h1'):
                headline = a['crawled_h1']
            elif a.get('crawled_title'):
                headline = a['crawled_title']
                
        rows.append({
            "ID": a.get('id'),
            "Source": a.get('original_source'),
            "Original Title": a.get('original_title'),
            "Web Headline/Topic": headline,
            "URL": a.get('url'),
            "Timestamp": a.get('timestamp'),
            "Crawl Status": a.get('crawl_status'),
            "Tag": a.get('assigned_tag') if a.get('assigned_tag') else "interesting"
        })
    df = pd.DataFrame(rows)
    df.to_excel(EXCEL_FILE, index=False)
    print(f"📊 Successfully synced and updated local Excel sheet: {EXCEL_FILE}")

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL or SUPABASE_KEY is missing from your .env file!")
        return

    print("🔌 Connecting to Supabase...")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/articles?order=id.asc"
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            articles = res.json()
            print(f"📥 Successfully fetched {len(articles)} articles from Supabase!")
            
            # Save to local JSON file
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            print(f"💾 Successfully updated local JSON database: {DB_FILE}")
            
            # Filter non-deleted for the Excel sheet
            non_deleted = [a for a in articles if not a.get("deleted_at")]
            sync_to_excel(non_deleted)
            
            print("✨ Sync complete! Your PC's local files are now perfectly in-sync with Supabase.")
        else:
            print(f"❌ Failed to fetch data: Status {res.status_code}")
            print(res.text)
    except Exception as e:
        print(f"❌ Connection error during sync: {e}")

if __name__ == "__main__":
    main()
