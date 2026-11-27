"""Script kiểm tra trạng thái chưng cất hiện tại."""
import sys, json, os, re, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8')

# Đọc API key
env_path = os.path.join('..', '.env') if os.path.exists(os.path.join('..', '.env')) else '.env'
key = os.environ.get('GEMINI_API_KEY', '').strip()
if not key and os.path.exists(env_path):
    for line in open(env_path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if line.startswith('GEMINI_API_KEY='):
            key = line.split('=', 1)[1].strip().strip('"').strip("'")
print(f'API key: {"OK (" + key[:18] + "...)" if key else "NOT FOUND"}')

# Dataset stats
ck = json.load(open('training/distill_checkpoint.json', encoding='utf-8'))
print(f'Checkpoint - passed: {len(ck["passed"])}, failed: {len(ck["failed"])}, teacher_dpo_pairs: {len(ck["teacher_dpo_pairs"])}')

d2 = json.load(open('training/dataset_dpo_preference.json', encoding='utf-8'))
print(f'DPO preference total: {len(d2)}')

# Test API key validity
if key:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
    payload = json.dumps({"contents": [{"role": "user", "parts": [{"text": "Say OK"}]}],
                          "generationConfig": {"maxOutputTokens": 10}}).encode('utf-8')
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            text = data['candidates'][0]['content']['parts'][0]['text']
            print(f'API test: OK -> "{text.strip()}"')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'API test FAILED: HTTP {e.code} - {body[:200]}')
    except Exception as ex:
        print(f'API test FAILED: {ex}')
