import os
import re
import json
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_FILE = "articles_database.json"
FINAL_FILE = "consolidated_categorized_articles.xlsx"
ENV_FILE = "/mnt/d/My Docs/Product Management/.env_global"

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

def get_groq_key():
    if not os.path.exists(ENV_FILE):
        return None
    with open(ENV_FILE, 'r') as f:
        content = f.read()
    match = re.search(r'GROQ_API_KEY=(gsk_[a-zA-Z0-9]+)', content)
    if match:
        return match.group(1)
    return None

def load_initial_data():
    """Load pocket and instapaper Excel files and unify them into a database."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    print("Initial database not found. Creating database from Excel files...")
    
    pocket_path = "pocket_articles.xlsx"
    instapaper_path = "instapaper_export.xlsx"
    
    articles = []
    
    # 1. Load Pocket
    if os.path.exists(pocket_path):
        df_pocket = pd.read_excel(pocket_path)
        print(f"Loaded {len(df_pocket)} articles from Pocket.")
        for idx, row in df_pocket.iterrows():
            title = str(row.get('title', '')).strip()
            url = str(row.get('url', '')).strip()
            time_added = str(row.get('time_added', '')).strip()
            
            if not url or url.lower() == 'nan':
                continue
                
            articles.append({
                "id": len(articles),
                "original_source": "pocket",
                "original_title": title if title and title.lower() != 'nan' else "Untitled",
                "url": url,
                "timestamp": time_added if time_added and time_added.lower() != 'nan' else "",
                "crawled_title": "",
                "crawled_h1": "",
                "crawl_status": "pending",
                "assigned_tag": ""
            })
            
    # 2. Load Instapaper
    if os.path.exists(instapaper_path):
        df_insta = pd.read_excel(instapaper_path)
        print(f"Loaded {len(df_insta)} articles from Instapaper.")
        for idx, row in df_insta.iterrows():
            title = str(row.get('Title', '')).strip()
            url = str(row.get('URL', '')).strip()
            timestamp = str(row.get('Timestamp', '')).strip()
            
            if not url or url.lower() == 'nan':
                continue
                
            articles.append({
                "id": len(articles),
                "original_source": "instapaper",
                "original_title": title if title and title.lower() != 'nan' else "Untitled",
                "url": url,
                "timestamp": timestamp if timestamp and timestamp.lower() != 'nan' else "",
                "crawled_title": "",
                "crawled_h1": "",
                "crawl_status": "pending",
                "assigned_tag": ""
            })
            
    # Save the consolidated list
    save_database(articles)
    print(f"Successfully consolidated {len(articles)} articles.")
    return articles

def save_database(articles):
    tmp_file = DB_FILE + ".tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    os.replace(tmp_file, DB_FILE)

def crawl_worker(article):
    """Worker to crawl a single article's URL for H1 and Title."""
    url = article['url']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    if not url.startswith('http://') and not url.startswith('https://'):
        return article['id'], "error_invalid_url", "", ""

    try:
        r = requests.get(url, headers=headers, timeout=1.5) # Fast 1.5s timeout!
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            title = ' '.join(title.split())
            
            h1s = [h1.get_text().strip() for h1 in soup.find_all('h1') if h1.get_text().strip()]
            h1 = h1s[0] if h1s else ""
            h1 = ' '.join(h1.split())
            
            return article['id'], "success", title, h1
        else:
            return article['id'], f"http_error_{r.status_code}", "", ""
    except requests.exceptions.Timeout:
        return article['id'], "error_timeout", "", ""
    except Exception as e:
        return article['id'], f"error_{type(e).__name__}", "", ""

def classify_batch_with_retry(api_key, batch_articles, max_retries=5):
    """Sends a batch of articles to Groq to be classified."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Format articles for the LLM
    formatted_list = []
    for a in batch_articles:
        title_to_use = a['original_title']
        if a['crawl_status'] == 'success':
            if a['crawled_h1']:
                title_to_use = a['crawled_h1']
            elif a['crawled_title']:
                title_to_use = a['crawled_title']
                
        formatted_list.append({
            "id": a['id'],
            "title": title_to_use,
            "url": a['url']
        })
        
    prompt = f"""
You are an expert article classifier. Classify each of the following articles into EXACTLY ONE of these categories:
{', '.join(TAGS)}

Classification Guidelines:
- psychology: Covers neuroscience, communication, soft skills, public speaking, confidence, introversion-extraversion, persuasion, emotional intelligence.
- tech/science: Covers hard sciences, quantum, breakthrough physics, civilisational history/discovery, tech related stuff, software development, coding, space.
- startup stories: Inspiring stories about startup founders, building specific companies, and startup journeys.
- startup vcs/sales: Venture capitalists, funding rounds, sales techniques, marketing strategies.
- geopoltics/history: Global politics, geopolitics, global history (except Indian history).
- indian politics: Politics, elections, and government in India.
- indian history: History, culture, ancient discoveries, and historical events of India.
- financial markets: Stocks, trading, investments, wall street, financial economics, macroeconomic markets.
- misanthropy: Misanthropic themes, essays observing human flaws with disgust/misanthropy.
- inspiration: Motivational articles, productivity, general wisdom, life lessons, personal growth.
- health: Diet, health, exercise, medicine, biology, wellness.
- literature: Books, reading, writers, literature reviews.
- hp: Strictly Harry Potter topics.
- music: Anything about music, bands, compositions.
- tennis: Tennis players, tournaments (Wimbledon, etc.).
- football: Football (soccer) clubs, players, leagues.
- cricket: Cricket matches, players, teams.
- formula 1: Formula 1 (F1) racing, drivers, teams.
- badminton: Badminton players, tournaments.
- cinema: Movie reviews, directors, filmmaking, films.
- interesting: The default fallback. Any articles that don't strictly or cleanly fall into any of the other tags MUST fall in the 'interesting' tag (such as cultural observation, op-eds, general essays).

CRITICAL EXCLUSIVITY RULE:
For 'hp', 'music', 'tennis', 'formula 1' (or F1), 'cricket', 'football', 'badminton', 'cinema':
They must be solely classified into these respective tags and remain exclusive to these tags. There should be NO overlap with others. If an article mentions any of these, put it in that specific tag.

Input articles to classify:
{json.dumps(formatted_list, indent=2)}

Output the result as a JSON object with a single key 'classifications' containing a list of objects, each with 'id' and 'tag'. Do not include any other text, markdown blocks, or explanation.
Example Output format:
{{
  "classifications": [
    {{"id": 0, "tag": "psychology"}},
    {{"id": 1, "tag": "interesting"}}
  ]
}}
"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                res_json = response.json()
                content = res_json['choices'][0]['message']['content'].strip()
                parsed = json.loads(content)
                if 'classifications' in parsed:
                    return parsed['classifications']
                else:
                    print(f"Warning: 'classifications' not found in response JSON: {parsed}")
            elif response.status_code == 429:
                print(f"Rate limited (429). Waiting 12 seconds to retry... (Attempt {attempt+1}/{max_retries})")
                time.sleep(12)
            else:
                print(f"Error {response.status_code}: {response.text}. Waiting 5 seconds...")
                time.sleep(5)
        except Exception as e:
            print(f"Exception during API call: {type(e).__name__}: {e}. Waiting 5 seconds...")
            time.sleep(5)
            
    return None

def sync_to_excel(articles):
    """Export the consolidated data to the final Excel file."""
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
    df.to_excel(FINAL_FILE, index=False)

def main():
    api_key = get_groq_key()
    if not api_key:
        print("CRITICAL: Groq API Key not found in .env_global!")
        return
        
    # 1. Load initial data
    articles = load_initial_data()
    total_articles = len(articles)
    
    # 2. Process in blocks of 40 (streaming pipeline)
    block_size = 40
    
    # Filter articles that are completely unprocessed
    # This allows resuming perfectly!
    pending_indices = [idx for idx, a in enumerate(articles) if a['crawl_status'] == 'pending' or not a.get('assigned_tag')]
    total_pending = len(pending_indices)
    
    if total_pending == 0:
        print("All articles have already been successfully processed.")
        sync_to_excel(articles)
        return
        
    print(f"Streaming Pipeline: Processing {total_pending} pending articles in blocks of {block_size}...")
    
    start_time = time.time()
    
    for i in range(0, total_pending, block_size):
        block_indices = pending_indices[i : i + block_size]
        block_articles = [articles[idx] for idx in block_indices]
        
        print(f"\n--- Processing Block {i//block_size + 1}/{(total_pending + block_size - 1)//block_size} (IDs: {block_articles[0]['id']} to {block_articles[-1]['id']}) ---")
        
        # A. Parallel Crawl the block of 40 (using 40 workers so they all run at once!)
        crawl_start = time.time()
        crawled_count = 0
        
        # Only crawl items that have pending crawl status
        to_crawl = [a for a in block_articles if a['crawl_status'] == 'pending']
        if to_crawl:
            print(f"Crawling {len(to_crawl)} websites in parallel...")
            with ThreadPoolExecutor(max_workers=len(to_crawl)) as executor:
                futures = {executor.submit(crawl_worker, a): a for a in to_crawl}
                for future in as_completed(futures):
                    art_id, status, crawled_title, crawled_h1 = future.result()
                    # Update local article list
                    for a in block_articles:
                        if a['id'] == art_id:
                            a['crawl_status'] = status
                            a['crawled_title'] = crawled_title
                            a['crawled_h1'] = crawled_h1
                            break
                    crawled_count += 1
            print(f"Crawl completed in {time.time() - crawl_start:.1f}s.")
        else:
            print("Crawl already completed for this block. Skipping...")
            
        # B. Batch Classify the block using Groq LLM
        print("Classifying block articles with Groq Llama-3.3...")
        classify_start = time.time()
        
        # Only classify items that don't have assigned tag
        to_classify = [a for a in block_articles if not a.get('assigned_tag')]
        if to_classify:
            classifications = classify_batch_with_retry(api_key, to_classify)
            if classifications:
                tag_map = {item['id']: item['tag'].strip().lower() for item in classifications if 'id' in item and 'tag' in item}
                
                # Standardize f1 -> formula 1 and check tag validity
                for item_id, tag in list(tag_map.items()):
                    if tag == 'f1':
                        tag_map[item_id] = 'formula 1'
                    elif tag not in TAGS:
                        # Find closest matching tag
                        matched = False
                        for t in TAGS:
                            if t in tag or tag in t:
                                tag_map[item_id] = t
                                matched = True
                                break
                        if not matched:
                            tag_map[item_id] = 'interesting'
                            
                # Save tags back into article database
                updated_count = 0
                for a in block_articles:
                    if a['id'] in tag_map:
                        a['assigned_tag'] = tag_map[a['id']]
                        updated_count += 1
                print(f"Classification completed in {time.time() - classify_start:.1f}s. Assigned {updated_count} tags.")
            else:
                print("Failed to classify this block. Setting default fallback tag 'interesting'.")
                for a in block_articles:
                    if not a.get('assigned_tag'):
                        a['assigned_tag'] = 'interesting'
        else:
            print("Classification already completed for this block. Skipping...")
            
        # C. Save database & Excel file atomically
        save_database(articles)
        sync_to_excel(articles)
        
        elapsed_total = time.time() - start_time
        processed_so_far = i + len(block_articles)
        avg_speed = processed_so_far / elapsed_total if elapsed_total > 0 else 0
        print(f"Block processed! Total progress: {processed_so_far}/{total_pending} ({processed_so_far/total_pending*100:.1f}%) | Avg speed: {avg_speed:.1f} articles/sec")
        
        # D. Respectful sleep of 2.0s to prevent Rate Limits
        time.sleep(2.0)
        
    print("\nAll articles successfully processed and synchronized with Excel!")

if __name__ == "__main__":
    main()
