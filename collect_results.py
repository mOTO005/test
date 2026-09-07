import csv,re,time,requests
from bs4 import BeautifulSoup

RACE_IDS = [
'202506010911','202508010611','202507020211','202509010811','202506020211',
'202506030111','202501010811','202505040211','202508030211','202505040611',
'202505010811','202509020411','202508020411','202505030211','202509030411',
'202506040911','202505041111','202507050211','202506010111','202507010111',
'202505010211','202505010411','202510011011','202504010511','202502010611',
'202503020611','202504020207','202501010511','202507030207','202505050311']

HEADERS={'User-Agent':'Mozilla/5.0 (compatible; results-dataset-research/1.0)','Referer':'https://race.netkeiba.com/'}
s=requests.Session(); s.headers.update(HEADERS)
result_rows=[]; payout_rows=[]; status=[]
BET_MAP={'単勝':'WIN','馬連':'QUINELLA','ワイド':'WIDE','馬単':'EXACTA','3連複':'TRIO','三連複':'TRIO','3連単':'TRIFECTA','三連単':'TRIFECTA'}

def txt(x): return x.get_text(' ',strip=True) if x else ''
def clean_int(v):
    m=re.search(r'\d+',v.replace(',','')); return int(m.group()) if m else None
def clean_money(v):
    m=re.search(r'[\d,]+',v); return int(m.group().replace(',','')) if m else None
def norm_combo(v):
    nums=re.findall(r'\d+',v); return '-'.join(str(int(n)) for n in nums) if nums else v.strip()

for rid in RACE_IDS:
    url=f'https://race.netkeiba.com/race/result.html?race_id={rid}'
    try:
        r=s.get(url,timeout=30); r.raise_for_status(); r.encoding='utf-8'
        soup=BeautifulSoup(r.text,'html.parser')
        title=txt(soup.select_one('h1.RaceName')) or txt(soup.find('h1'))
        table=soup.select_one('table.RaceTable01') or soup.select_one('#All_Result_Table') or soup.find('table',class_='race_table_01')
        if not table: raise ValueError('result table not found')
        trs=table.find_all('tr')
        headers=[txt(x) for x in trs[0].find_all(['th','td'])]
        def idx(names):
            for n in names:
                for i,h in enumerate(headers):
                    if n==h or n in h: return i
            return None
        i_finish=idx(['着順']); i_no=idx(['馬番']); i_name=idx(['馬名'])
        if None in (i_finish,i_no,i_name): raise ValueError(f'columns missing {headers}')
        rcount0=len(result_rows); pcount0=len(payout_rows)
        for tr in trs[1:]:
            tds=tr.find_all('td'); vals=[txt(x) for x in tds]
            if not vals or max(i_finish,i_no,i_name)>=len(vals): continue
            horse_no=clean_int(vals[i_no]); horse_name=vals[i_name]; finish=vals[i_finish]
            if horse_no is None or not horse_name: continue
            result_rows.append([rid,title,finish,horse_no,horse_name,url])

        # payout rows: netkeiba static result page tables
        for tr in soup.find_all('tr'):
            cells=tr.find_all(['th','td']); vals=[txt(c) for c in cells]
            if len(vals)<3: continue
            label=vals[0].replace(' ',''); bt=None
            for jp,mapped in BET_MAP.items():
                if jp in label: bt=mapped; break
            if not bt: continue
            combos=re.findall(r'\d+',vals[1]); payouts=re.findall(r'[\d,]+円',vals[2])
            # Wide can contain 3 combinations and 3 payouts in one row.
            if bt=='WIDE' and len(combos)>=6 and len(payouts)>=3:
                pairs=[combos[0:2],combos[2:4],combos[4:6]]
                for pair,pay in zip(pairs,payouts[:3]):
                    payout_rows.append([rid,title,bt,'-'.join(str(int(x)) for x in pair),clean_money(pay),url])
            else:
                combo=norm_combo(vals[1]); payout=clean_money(vals[2])
                if combo and payout is not None: payout_rows.append([rid,title,bt,combo,payout,url])
        status.append([rid,'OK',title,len(result_rows)-rcount0,len(payout_rows)-pcount0,''])
    except Exception as e:
        status.append([rid,'ERROR','',0,0,str(e)[:500]])
    time.sleep(0.35)

with open('race_results_30r.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Race_Name','Finish_Position','Horse_No','Horse_Name','Source_URL']); w.writerows(result_rows)
with open('payouts_30r.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Race_Name','Bet_Type','Winning_Combination','Payout_per_100yen','Source_URL']); w.writerows(payout_rows)
with open('results_collection_status.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Status','Race_Name','Result_Rows','Payout_Rows','Error']); w.writerows(status)
print('races ok',sum(1 for x in status if x[1]=='OK'),'/',len(status),'result rows',len(result_rows),'payout rows',len(payout_rows))
if any(x[1]!='OK' for x in status): raise SystemExit(2)
