import urllib.request, json, os
key = os.getenv("GEMINI_API_KEY", "")
if not key and os.path.exists("gemini_api_key.txt"):
    with open("gemini_api_key.txt", "r", encoding="utf-8") as f:
        key = f.read().strip()
try:
    r = urllib.request.urlopen(urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models?key={key}'))
    d = json.loads(r.read().decode('utf-8'))
    for m in d.get('models',[]):
        if 'generateContent' in m.get('supportedGenerationMethods',[]) and 'gemini' in m['name'].lower() and 'flash' in m['name'].lower():
            name = m['name']
            try:
                url = f'https://generativelanguage.googleapis.com/v1beta/{name}:generateContent?key={key}'
                req = urllib.request.Request(url, method='POST', headers={'Content-Type': 'application/json'}, data=json.dumps({'contents':[{'parts':[{'text':'Hello'}]}]}).encode('utf-8'))
                res = urllib.request.urlopen(req)
                print('WORKS:', name)
            except Exception as e:
                print('FAILS:', name, str(e))
except Exception as e:
    print("FAILED TO GET MODELS", e)
