import urllib.request, json, os

key = os.getenv("GEMINI_API_KEY", "")
if not key and os.path.exists("gemini_api_key.txt"):
    with open("gemini_api_key.txt", "r", encoding="utf-8") as f:
        key = f.read().strip()

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))
    for m in data.get('models', []):
        if 'gemini' in m['name']:
            print(m['name'])
