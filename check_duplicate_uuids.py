import json
from collections import Counter

def find_duplicate_uuids(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    uuids = []
    def collect_uuids(item):
        if isinstance(item, dict):
            if 'uuid' in item:
                uuids.append(item['uuid'])
            for v in item.values():
                collect_uuids(v)
        elif isinstance(item, list):
            for v in item:
                collect_uuids(v)
    collect_uuids(data)
    counter = Counter(uuids)
    dups = [uuid for uuid, count in counter.items() if count > 1]
    if dups:
        print('Duplicate UUIDs found:', dups)
    else:
        print('No duplicate UUIDs found.')

if __name__ == '__main__':
    find_duplicate_uuids('projects/project_d32c662c-e8d6-4b00-b2e7-e91ae7e199cb.json')
