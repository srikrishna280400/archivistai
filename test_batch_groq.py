import requests
import json
import re

def get_groq_key():
    with open('/mnt/d/My Docs/Product Management/.env_global', 'r') as f:
        content = f.read()
    match = re.search(r'GROQ_API_KEY=(gsk_[a-zA-Z0-9]+)', content)
    if match:
        return match.group(1)
    return None

def test_batch():
    key = get_groq_key()
    if not key:
        print("Groq API key not found!")
        return
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    tags = [
        "psychology", "music", "geopoltics/history", "inspiration", "tennis",
        "football", "cricket", "formula 1", "badminton", "cinema",
        "indian politics", "indian history", "tech/science", "interesting",
        "literature", "hp", "startup stories", "financial markets",
        "misanmisanthropy", "startup vcs/sales", "health"
    ]
    
    articles = [
        {"id": 101, "title": "The Science of Sleep and Memory", "url": "http://sleep.com"},
        {"id": 102, "title": "Nadal wins French Open in epic final", "url": "http://tennis.com"},
        {"id": 103, "title": "Why Startups Fail: Insights from VCs", "url": "http://vcs.com"},
        {"id": 104, "title": "The Rise and Fall of the Roman Empire", "url": "http://history.com"},
        {"id": 105, "title": "A review of Harry Potter and the Deathly Hallows", "url": "http://hp.com"}
    ]
    
    prompt = f"""
You are an expert article classifier. Classify each of the following articles into EXACTLY ONE of these tags:
{', '.join(tags)}

Rules:
- psychology tag covers neuroscience, communication, soft skills, confidence, introversion-extraversion.
- tech/science tag covers hard sciences, quantum, civilisational history/discovery, breakthrough physics, tech related stuff.
- startup vcs/sales covers venture capitalists, sales.
- hp means Harry Potter.
- f1 or Formula 1 must be categorized as 'formula 1'.
- Any articles that don't strictly or cleanly fall into any of these tags must fall in the 'interesting' tag (e.g. culture observation, op-eds).
- For hp, music, tennis, formula 1, cricket, football, badminton, cinema, they must be solely and exclusively within these tags (no overlap or other tag).

Input articles to classify:
{json.dumps(articles, indent=2)}

Output the result as a JSON object with a single key 'classifications' containing a list of objects, each with 'id' and 'tag'. Do not include any other text or explanation.
Example:
{{
  "classifications": [
    {{"id": 101, "tag": "psychology"}},
    ...
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
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("Success! JSON response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print("Error:", response.status_code)
        print(response.text)

if __name__ == "__main__":
    test_batch()
