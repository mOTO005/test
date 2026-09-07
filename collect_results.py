import csv,re,time,requests
from bs4 import BeautifulSoup

RACE_IDS = [
'202506010911','202508010611','202507020211','202509010811','202506020211',
'202506030111','202501010811','202505040211','202508030211','202505040611',
'202505010811','202509020411','202508020411','202505030211','202509030411',
'202506040911','202505041111','202507050211','202506010111','202507010111',
'202505010211','202505010411','202510011011','202504010511','202502010611',
'202503020611','202504020207','202501010511','202507030207','202505050311']

HEADERS={
 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36',
 'Accept-Language':'ja,en-US;q=0.8,en;q=0.6','Referer':'https://db.netkeiba.com/'
}
s=requests.Session(); s.headers.update(HEADERS)
result_rows=[]; payout_rows=[]; status=[]; top5_rows=[]
BET_MAP={'単勝':'WIN','馬連':'QUINELLA','ワイド':'WIDE','馬単':'EXACTA','3連複':'TRIO','三連複':'TRIO','3連単':'TRIFECTA','三連単':'TRIFECTA'}

def txt(x): return x.get_text(' ',strip=True) if x else ''
def compact(v): return re.sub(r'\s+','',v or '')
def clean_int(v):
    m=re.search(r'\d+',str(v).replace(',','')); return int(m.group()) if m else None
def clean_money(v):
    m=re.search(r'[\d,]+',v); return int(m.group().replace(',','')) if m else None
def norm_combo(v):
    nums=re.findall(r'\d+',v); return '-'.join(str(int(n)) for n in nums) if nums else v.strip()

def val(vals,i): return vals[i] if i is not None and i < len(vals) else ''

def parse_finish(v):
    v=compact(v)
    return int(v) if v.isdigit() else None

for rid in RACE_IDS:
    url=f'https://db.netkeiba.com/race/{rid}/'
    try:
        r=s.get(url,timeout=30); r.raise_for_status()
        try: html=r.content.decode('euc_jp')
        except UnicodeDecodeError: html=r.content.decode('cp932',errors='replace')
        soup=BeautifulSoup(html,'html.parser')
        title=txt(soup.select_one('.racedata h1')) or txt(soup.select_one('h1'))
        table=soup.select_one('table.race_table_01')
        if not table: raise ValueError('result table not found')
        trs=table.find_all('tr')
        headers=[txt(x) for x in trs[0].find_all(['th','td'])]
        cheaders=[compact(h) for h in headers]
        def idx(names):
            for n in [compact(x) for x in names]:
                for i,h in enumerate(cheaders):
                    if n==h or n in h: return i
            return None
        I={
          'finish':idx(['着順']),'frame':idx(['枠番']),'no':idx(['馬番']),'name':idx(['馬名']),
          'sexage':idx(['性齢']),'weight':idx(['斤量']),'jockey':idx(['騎手']),'time':idx(['タイム']),
          'margin':idx(['着差']),'passing':idx(['通過']),'last3f':idx(['上り']),'odds':idx(['単勝']),
          'pop':idx(['人気']),'body':idx(['馬体重']),'trainer':idx(['調教師'])
        }
        if None in (I['finish'],I['no'],I['name']): raise ValueError(f'columns missing {headers}')
        rcount0=len(result_rows); pcount0=len(payout_rows)
        race_rows=[]
        for tr in trs[1:]:
            vals=[txt(x) for x in tr.find_all('td')]
            if not vals: continue
            horse_no=clean_int(val(vals,I['no'])); horse_name=val(vals,I['name']); finish_raw=compact(val(vals,I['finish']))
            if horse_no is None or not horse_name: continue
            finish_num=parse_finish(finish_raw)
            identity=f'{rid}|{horse_no}|{horse_name}'
            row=[rid,title,finish_raw,finish_num,horse_no,horse_name,identity,
                 clean_int(val(vals,I['frame'])),val(vals,I['sexage']),val(vals,I['weight']),val(vals,I['jockey']),
                 val(vals,I['time']),val(vals,I['margin']),val(vals,I['passing']),val(vals,I['last3f']),
                 val(vals,I['body']),val(vals,I['trainer']),url]
            result_rows.append(row); race_rows.append(row)
        top5=sorted([x for x in race_rows if isinstance(x[3],int) and 1 <= x[3] <= 5], key=lambda x:x[3])
        summary=[rid,title]
        for pos in range(1,6):
            rr=next((x for x in top5 if x[3]==pos),None)
            summary += [rr[4] if rr else '', rr[5] if rr else '', rr[6] if rr else '', rr[11] if rr else '', rr[12] if rr else '', rr[14] if rr else '']
        top5_rows.append(summary)

        for tr in soup.find_all('tr'):
            vals=[txt(c) for c in tr.find_all(['th','td'])]
            if len(vals)<3: continue
            label=compact(vals[0]); bt=None
            for jp,mapped in BET_MAP.items():
                if compact(jp) in label: bt=mapped; break
            if not bt: continue
            combo_nums=re.findall(r'\d+',vals[1]); payouts=re.findall(r'[\d,]+円',vals[2])
            if bt=='WIDE' and len(combo_nums)>=6 and len(payouts)>=3:
                for pair,pay in zip([combo_nums[0:2],combo_nums[2:4],combo_nums[4:6]],payouts[:3]):
                    payout_rows.append([rid,title,bt,'-'.join(str(int(x)) for x in pair),clean_money(pay),url])
            else:
                combo=norm_combo(vals[1]); payout=clean_money(vals[2])
                if combo and payout is not None: payout_rows.append([rid,title,bt,combo,payout,url])
        status.append([rid,'OK',title,len(result_rows)-rcount0,len(payout_rows)-pcount0,''])
    except Exception as e:
        status.append([rid,'ERROR','',0,0,str(e)[:500]])
    time.sleep(0.20)

with open('race_results_30r_pdca.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Race_Name','Finish_Position_Raw','Finish_Position','Horse_No','Horse_Name','Canonical_Horse_Identity','Frame_No','Sex_Age','Carried_Weight','Jockey','Finish_Time','Margin','Passing_Order','Last3F','Body_Weight','Trainer','Source_URL']); w.writerows(result_rows)
with open('race_top5_summary_30r.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f)
    hdr=['Race_ID','Race_Name']
    for p in range(1,6): hdr += [f'P{p}_Horse_No',f'P{p}_Horse_Name',f'P{p}_Canonical_Identity',f'P{p}_Finish_Time',f'P{p}_Margin',f'P{p}_Last3F']
    w.writerow(hdr); w.writerows(top5_rows)
with open('payouts_30r.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Race_Name','Bet_Type','Winning_Combination','Payout_per_100yen','Source_URL']); w.writerows(payout_rows)
with open('results_collection_status.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Race_ID','Status','Race_Name','Result_Rows','Payout_Rows','Error']); w.writerows(status)
print('races ok',sum(1 for x in status if x[1]=='OK'),'/',len(status),'result rows',len(result_rows),'top5 rows',len(top5_rows),'payout rows',len(payout_rows))
for row in status:
    if row[1] != 'OK': print('ERROR',row[0],row[5])
