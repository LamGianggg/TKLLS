"""Test model availability."""
import sys, json, urllib.request, urllib.error, os
sys.stdout.reconfigure(encoding='utf-8')

key = ''
for line in open('.env', encoding='utf-8', errors='replace'):
    if line.strip().startswith('GEMINI_API_KEY='):
        key = line.strip().split('=', 1)[1].strip().strip('"').strip("'")

models = [
    'gemini-3.1-flash-lite',
    'gemini-3-flash-preview',
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash-lite-preview-06-17',
    'gemini-2.5-pro',
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
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data['candidates'][0]['content']['parts'][0]['text']
            print(f'[OK]  {model}: "{text.strip()}"')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:180]
        print(f'[{e.code}] {model}: {body}')
    except Exception as ex:
        print(f'[ERR] {model}: {ex}')
