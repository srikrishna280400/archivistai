import json
import os

def check():
    if not os.path.exists("articles_database.json"):
        print("articles_database.json does not exist yet.")
        return
    with open("articles_database.json", "r", encoding="utf-8") as f:
        try:
            db = json.load(f)
            total = len(db)
            crawled = sum(1 for a in db if a.get('crawl_status') != 'pending')
            classified = sum(1 for a in db if a.get('assigned_tag') != '')
            success = sum(1 for a in db if a.get('crawl_status') == 'success')
            failed = sum(1 for a in db if a.get('crawl_status') != 'pending' and a.get('crawl_status') != 'success')
            print(f"Total: {total}")
            print(f"Crawled: {crawled}/{total} (Success: {success}, Failed: {failed})")
            print(f"Classified: {classified}/{total}")
        except Exception as e:
            print("Error loading database:", e)

if __name__ == "__main__":
    check()
