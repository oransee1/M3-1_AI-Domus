import urllib.request, urllib.error, json, os

key = os.getenv("GEMINI_API_KEY", "")
if not key and os.path.exists("gemini_api_key.txt"):
    with open("gemini_api_key.txt", "r", encoding="utf-8") as f:
        key = f.read().strip()

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
data = json.dumps({'contents':[{'parts':[{'text':'Hello'}]}]}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
req = urllib.request.Request(url, method='POST', headers=headers, data=data)

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode('utf-8'))
