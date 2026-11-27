"""Kiểm tra số spec còn pending chưa chưng cất."""
import sys, json, os, re
sys.stdout.reconfigure(encoding='utf-8')

# Load checkpoint
ck = json.load(open('training/distill_checkpoint.json', encoding='utf-8'))
done_ids = {item['id'] for item in ck.get('passed', [])}
done_ids.update(item['id'] for item in ck.get('failed', []))
print(f'Đã xử lý: {len(done_ids)} (passed: {len(ck["passed"])}, failed: {len(ck["failed"])})')

# Kiểm tra VerilogDB cache
cache_path = 'training/verilogdb_selected_candidates.json'
full_pool_path = 'training/verilogdb_full_clean_pool.json'
if os.path.exists(cache_path):
    cached = json.load(open(cache_path, encoding='utf-8'))
    cached_ids = {c['id'] for c in cached}
    pending_vdb = [c for c in cached if c['id'] not in done_ids]
    print(f'VerilogDB cache: {len(cached)} mẫu, còn pending: {len(pending_vdb)}')
else:
    print('VerilogDB cache: KHÔNG CÓ')

if os.path.exists(full_pool_path):
    full_pool = json.load(open(full_pool_path, encoding='utf-8'))
    pending_full = [c for c in full_pool if f"distill_vdb_{c['module_name']}" not in done_ids]
    # Group by category
    cats = {}
    for c in pending_full:
        cats[c['category']] = cats.get(c['category'], 0) + 1
    print(f'Full pool sạch: {len(full_pool)} mẫu, còn pending: {len(pending_full)}')
    print('Top 5 họ mạch chưa làm:')
    for k, v in sorted(cats.items(), key=lambda x: -x[1])[:5]:
        print(f'  {k}: {v}')
else:
    print('Full pool: KHÔNG CÓ')
