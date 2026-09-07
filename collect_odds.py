import csv, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import requests

RACE_IDS = [
'202506010911','202508010611','202507020211','202509010811','202506020211',
'202506030111','202501010811','202505040211','202508030211','202505040611',
'202505010811','202509020411','202508020411','202505030211','202509030411',
'202506040911','202505041111','202507050211','202506010111','202507010111',
'202505010211','202505010411','202510011011','202504010511','202502010611',
'202503020611','202504020207','202501010511','202507030207','202505050311']

BET_TYPES = {
  '1':'WIN',
  '4':'QUINELLA',
  '5':'WIDE',
  '6':'EXACTA',
  '7':'TRIO',
  '8':'TRIFECTA',
}

URL='https://race.netkeiba.com/api/api_get_jra_odds.html'
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; historical-odds-research/1.0)','Referer':'https://race.netkeiba.com/'}

def fetch_one(rid, typ, name):
    fetched_at=datetime.now(timezone.utc).isoformat()
    try:
        r=requests.get(URL,params={'race_id':rid,'type':typ,'action':'update'},headers=HEADERS,timeout=10)
        r.raise_for_status()
        p=r.json()
        odds=(p.get('data') or {}).get('odds')
        if odds is None:
            raise ValueError('data.odds missing')
        rec={'race_id':rid,'bet_type':name,'api_type':typ,'fetched_at_utc':fetched_at,'odds':odds}
        stat=[rid,name,'OK',len(json.dumps(odds,ensure_ascii=False)),fetched_at,'']
        return rec, stat
    except Exception as e:
        return None, [rid,name,'ERROR',0,fetched_at,str(e)[:300]]

jobs=[(rid,typ,name) for rid in RACE_IDS for typ,name in BET_TYPES.items()]
records=[]; status=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    futs={ex.submit(fetch_one,*j):j for j in jobs}
    for fut in as_completed(futs):
        rec, stat=fut.result()
        status.append(stat)
        if rec is not None:
            records.append(rec)

records.sort(key=lambda x:(RACE_IDS.index(x['race_id']), int(x['api_type'])))
status.sort(key=lambda x:(RACE_IDS.index(x[0]), list(BET_TYPES.values()).index(x[1])))

with open('historical_odds_raw.json','w',encoding='utf-8') as f:
    json.dump({'source':'netkeiba odds API data.odds only','result_fields_saved':False,'records':records},f,ensure_ascii=False,separators=(',',':'))
with open('historical_odds_status.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Bet_Type','Status','Odds_Payload_Bytes','Fetched_At_UTC','Error']); w.writerows(status)

ok=sum(1 for x in status if x[2]=='OK')
print(f'OK={ok}/{len(status)}')
if ok != len(status):
    raise SystemExit(2)
