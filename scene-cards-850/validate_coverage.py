import json,collections
from pathlib import Path
root=Path(__file__).resolve().parent
plan=json.loads((root/'cards_plan.json').read_text(encoding='utf-8'))
source=json.loads((root/'words_850.json').read_text(encoding='utf-8'))
expected={x['word'] for x in source['words']}
cards=plan['cards']; count=collections.Counter(w for c in cards for w in c['primary_words'])
report={'cards':len(cards),'unique_words':len(count),'assignments':sum(count.values()),'missing':sorted(expected-set(count)),'extra':sorted(set(count)-expected),'duplicates':{w:n for w,n in count.items() if n>1}}
print(json.dumps(report,ensure_ascii=False,indent=2))
assert len(cards)==100 and len({c['id'] for c in cards})==100
assert len(expected)==850 and len(count)==850 and sum(count.values())==850
assert not report['missing'] and not report['extra'] and not report['duplicates']
for c in cards:
 assert c['target_count']==len(c['primary_words'])
 assert [t['word'] for t in c['targets']]==c['primary_words']
print('PASS: planned headword coverage only; content and images still require review.')
