import requests
import re

def get_groq_key():
    with open('/mnt/d/My Docs/Product Management/.env_global', 'r') as f:
        content = f.read()
    match = re.search(r'GROQ_API_KEY=(gsk_[a-zA-Z0-9]+)', content)
    if match:
        return match.group(1)
    return None

def test_groq():
    key = get_groq_key()
    if not key:
        print("Groq API key not found in .env_global!")
        return
    
    print("Found key:", key[:10] + "...")
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
    
    # Let's test a simple classification
    test_title = "The Neuroscience of Silence: How Solitude Helps the Brain Recover"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": f"You are a precise classifier. Categorize this web article title: '{test_title}' into exactly one of the following tags:\n"
                           f"{', '.join(tags)}\n\n"
                           f"Return ONLY the exact tag name, nothing else."
            }
        ],
        "temperature": 0.0
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("Success! Response:")
        print(response.json()['choices'][0]['message']['content'].strip())
    else:
        print("Error:", response.status_code)
        print(response.text)

if __name__ == "__main__":
    test_groq()
