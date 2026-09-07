import csv, json
from collections import Counter, defaultdict

TYPE_OUTER={'WIN':'1','QUINELLA':'4','WIDE':'5','EXACTA':'6','TRIO':'7','TRIFECTA':'8'}
SENTINEL={'WIDE':9999.9,'QUINELLA':99999.9,'EXACTA':99999.9,'TRIO':99999.9,'TRIFECTA':999999.9}

def num(s):
    if s is None or s=='': return None
    return float(str(s).replace(',',''))

def combo_text(bt,key):
    parts=[key[i:i+2] for i in range(0,len(key),2)]
    if bt=='WIN': return parts[0]
    if bt in ('EXACTA','TRIFECTA'): return '>'.join(parts)
    return '-'.join(parts)

with open('historical_odds_raw.json',encoding='utf-8') as f:
    raw=json.load(f)

rows=[]; audit=[]; stats=defaultdict(lambda:Counter())
for rec in raw['records']:
    rid=rec['race_id']; bt=rec['bet_type']; outer=TYPE_OUTER[bt]
    book=rec['odds'].get(outer,{})
    for key,val in book.items():
        lo=num(val[0]) if len(val)>0 else None
        hi=num(val[1]) if len(val)>1 else None
        if hi==0.0: hi=None
        reason=''
        valid=True
        if lo is None or lo<=0:
            valid=False; reason='NONPOSITIVE_OR_MISSING'
        sent=SENTINEL.get(bt)
        if sent is not None and lo is not None and abs(lo-sent)<1e-6:
            valid=False; reason='NETKEIBA_SENTINEL'
        stats[(rid,bt)]['raw']+=1
        if valid:
            stats[(rid,bt)]['valid']+=1
            rows.append([rid,bt,combo_text(bt,key),key,lo,'' if hi is None else hi,
                         'HISTORICAL_FINAL_ARCHIVE','netkeiba odds API',rec['fetched_at_utc'],'FALSE','FALSE','PASS'])
        else:
            stats[(rid,bt)]['invalid']+=1
            audit.append([rid,bt,key,'' if lo is None else lo,'' if hi is None else hi,reason])

with open('historical_odds_normalized.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f)
    w.writerow(['Race_ID','Bet_Type','Combination','Raw_Combination_Key','Odds_Lower','Odds_Upper','Odds_Type','Odds_Source','Source_Retrieved_At_UTC','Result_Fields_Saved','Popularity_Used','Market_Leak_Status'])
    w.writerows(rows)
with open('historical_odds_invalid_rows.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Bet_Type','Raw_Combination_Key','Odds_Lower','Odds_Upper','Invalid_Reason']); w.writerows(audit)
with open('historical_odds_integrity.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Bet_Type','Raw_Count','Valid_Count','Invalid_Count'])
    for (rid,bt),c in sorted(stats.items()): w.writerow([rid,bt,c['raw'],c['valid'],c['invalid']])
print('VALID_ROWS',len(rows),'INVALID_ROWS',len(audit),'RACE_TYPE_BLOCKS',len(stats))
