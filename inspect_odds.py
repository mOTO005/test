import json

with open('historical_odds_raw.json',encoding='utf-8') as f:
    data=json.load(f)

summary={}
for rec in data['records']:
    bt=rec['bet_type']
    if bt in summary: continue
    odds=rec['odds']
    outer_key='1' if bt=='WIN' else rec['api_type']
    inner=odds[outer_key]
    first_key=next(iter(inner))
    summary[bt]={'outer_key':outer_key,'first_combination_key':first_key,'full_value':inner[first_key]}

with open('odds_schema_summary.json','w',encoding='utf-8') as f:
    json.dump(summary,f,ensure_ascii=False,indent=2)
print(json.dumps(summary,ensure_ascii=False))
