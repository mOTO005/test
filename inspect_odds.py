import json

with open('historical_odds_raw.json',encoding='utf-8') as f:
    data=json.load(f)

summary={}
for rec in data['records']:
    bt=rec['bet_type']
    if bt in summary: continue
    odds=rec['odds']
    def desc(x,depth=0):
        if depth>3: return type(x).__name__
        if isinstance(x,dict):
            keys=list(x.keys())[:3]
            return {'type':'dict','keys':keys,'samples':{k:desc(x[k],depth+1) for k in keys}}
        if isinstance(x,list):
            return {'type':'list','len':len(x),'sample':desc(x[0],depth+1) if x else None}
        return {'type':type(x).__name__,'value':x}
    summary[bt]=desc(odds)

with open('odds_schema_summary.json','w',encoding='utf-8') as f:
    json.dump(summary,f,ensure_ascii=False,indent=2)
print(json.dumps(summary,ensure_ascii=False))
