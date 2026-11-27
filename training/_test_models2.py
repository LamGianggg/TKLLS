"""Test additional new model names."""
import sys, json, urllib.request, urllib.error, os, time
sys.stdout.reconfigure(encoding='utf-8')

key = ''
for line in open('.env', encoding='utf-8', errors='replace'):
    if line.strip().startswith('GEMINI_API_KEY='):
        key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")

models = [
    'gemini-3-flash-preview',
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash-lite',
    'gemini-3.8-flash',
    'gemini-3.1-pro-preview',
    'gemini-3.5-flash',
]

for model in models:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    body_dict = {
        'contents': [{'role': 'user', 'parts': [{'text': 'Reply: OK'}]}],
        'generationConfig': {'maxOutputTokens': 5}
    }
    payload = json.dumps(body_dict).encode('utf-8')
    req = urllib.request.Request(
        url, data=payload,
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            text = data['candidates'][0]['content']['parts'][0]['text']
            print(f'[OK]  {model}: "{text.strip()}"')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:180]
        print(f'[{e.code}] {model}: {body}')
    except Exception as ex:
        print(f'[ERR] {model}: {ex}')
    time.sleep(1)
