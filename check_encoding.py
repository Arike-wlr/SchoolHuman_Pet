import json

with open('高校拟人角色_fixed.json', 'r', encoding='utf-8') as f:
    content = f.read()

obj = json.loads(content)
print(f'Parsed {len(obj)} items')

first = obj[0]
keys = list(first.keys())
print('Keys:', keys)

# Check if keys are readable
try:
    name_key = '姓名'
    school_key = '代表高校'
    print(f'Has 姓名 key: {name_key in first}')
    print(f'Has 代表高校 key: {school_key in first}')
except Exception as e:
    print(f'Key check error: {e}')

# Show raw bytes of first key
first_key_bytes = keys[0].encode('utf-8')
print(f'First key bytes: {first_key_bytes.hex()}')
print(f'First key as gb18030 decode: {first_key_bytes.decode("gb18030", errors="replace")}')
