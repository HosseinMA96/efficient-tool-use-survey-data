#!/usr/bin/env python3
"""Reproducible arXiv harvest. Usage: harvest.py <config.json> <out_dir>
config: {"window": ["YYYYMMDD","YYYYMMDD"], "queries": {"Q1": "abs:\"...\"", ...},
         "title_regex": "<regex marking topic-centric titles>"}"""
import sys, json, time, re, csv, collections, urllib.request, urllib.parse, xml.etree.ElementTree as ET
NS={'a':'http://www.w3.org/2005/Atom','o':'http://a9.com/-/spec/opensearch/1.1/'}
cfg=json.load(open(sys.argv[1])); out=sys.argv[2]
DATE=f'submittedDate:[{cfg["window"][0]}0000 TO {cfg["window"][1]}2359]'
recs={}; counts={}
for qid,q in cfg['queries'].items():
    start=0; got=0
    while True:
        url='http://export.arxiv.org/api/query?'+urllib.parse.urlencode({'search_query':f'({q}) AND {DATE}','start':start,'max_results':1000,'sortBy':'submittedDate','sortOrder':'ascending'})
        for t in range(5):
            try: root=ET.fromstring(urllib.request.urlopen(url,timeout=180).read()); break
            except Exception: time.sleep(6)
        total=int(root.find('o:totalResults',NS).text); es=root.findall('a:entry',NS)
        for e in es:
            i=e.find('a:id',NS).text.split('/abs/')[-1].split('v')[0]
            r=recs.setdefault(i,{'id':i,'title':' '.join(e.find('a:title',NS).text.split()),'published':e.find('a:published',NS).text[:10],'abstract':' '.join(e.find('a:summary',NS).text.split()),'queries':set()})
            r['queries'].add(qid)
        got+=len(es); start+=1000
        if got>=total or not es or got>=10000: break
        time.sleep(3.5)
    counts[qid]=total; print(qid,total,file=sys.stderr); time.sleep(3.5)
rx=re.compile(cfg['title_regex'],re.I)
rows=[]; q=collections.Counter()
for r in recs.values():
    c=bool(rx.search(r['title'])); rows.append({**r,'queries':';'.join(sorted(r['queries'])),'topic_centric':c})
    if c: y,m=int(r['published'][:4]),int(r['published'][5:7]); q[f"{y}Q{(m-1)//3+1}"]+=1
json.dump({'config':cfg,'counts':counts,'records':[{**r} for r in rows]},open(f'{out}/harvest.json','w'))
with open(f'{out}/screening.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['id','published','title','queries','topic_centric','abstract']); w.writeheader(); w.writerows(rows)
print(json.dumps({'identified':sum(counts.values()),'per_query':counts,'unique':len(rows),'topic_centric':sum(r['topic_centric'] for r in rows),'quarterly_topic_centric':dict(sorted(q.items()))},indent=1))
