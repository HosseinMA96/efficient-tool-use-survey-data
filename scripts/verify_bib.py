#!/usr/bin/env python3
"""Verify every arXiv-backed entry of references.bib against the arXiv API.

For each entry with an arXiv identifier (eprint, journal or url field) we
fetch the arXiv record and compare (i) the title (normalized similarity) and
(ii) the first author's surname.  Entries without an arXiv ID are listed with
their DOI/URL for manual or Crossref checking.

Usage: python3 verify_bib.py ../paper/references.bib [arxiv|s2] > verify_bib_report.tsv
(s2 = Semantic Scholar batch lookup by arXiv ID, for when the arXiv API rate-limits)
"""
import difflib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

NS = {"a": "http://www.w3.org/2005/Atom"}


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"\\[a-zA-Z]+\s*|[{}$\\]", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def surname(author_field):
    first = author_field.split(" and ")[0].strip()
    if "," in first:
        name = first.split(",")[0]
    else:
        name = first.split()[-1] if first.split() else first
    return norm(name)


bib = open(sys.argv[1]).read()
entries = re.findall(r"@(\w+)\{([^,]+),(.*?)\n\}", bib, re.S)
recs = []
for typ, key, body in entries:
    f = dict((k.lower(), v) for k, v in re.findall(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", body))
    ax = None
    for fld in ("eprint", "journal", "url", "note"):
        m = re.search(r"(\d{4}\.\d{4,5})", f.get(fld, ""))
        if m:
            ax = m.group(1)
            break
    recs.append((key, typ, f, ax))

ids = sorted({r[3] for r in recs if r[3]})
meta = {}
SOURCE = sys.argv[2] if len(sys.argv) > 2 else "arxiv"


def fetch_arxiv(batch):
    url = ("https://export.arxiv.org/api/query?max_results=100&id_list=" + ",".join(batch))
    req = urllib.request.Request(url, headers={"User-Agent": "bib-verify-script"})
    for attempt in range(6):
        try:
            xml = urllib.request.urlopen(req, timeout=60).read()
            break
        except urllib.error.HTTPError as err:
            if err.code not in (301, 429, 503) or attempt == 5:
                raise
            time.sleep(60 * (attempt + 1))
    for e in ET.fromstring(xml).findall("a:entry", NS):
        aid = re.search(r"(\d{4}\.\d{4,5})", e.find("a:id", NS).text).group(1)
        title = " ".join(e.find("a:title", NS).text.split())
        authors = [a.find("a:name", NS).text for a in e.findall("a:author", NS)]
        meta[aid] = (title, authors)


def fetch_s2(batch):
    """Fallback when the arXiv API rate-limits: Semantic Scholar batch lookup by arXiv ID."""
    import json
    body = json.dumps({"ids": [f"ARXIV:{x}" for x in batch]}).encode()
    req = urllib.request.Request(
        "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,authors,externalIds",
        data=body, headers={"Content-Type": "application/json", "User-Agent": "bib-verify-script"})
    for attempt in range(6):
        try:
            res = json.loads(urllib.request.urlopen(req, timeout=60).read())
            break
        except urllib.error.HTTPError as err:
            if err.code not in (429, 503) or attempt == 5:
                raise
            time.sleep(30 * (attempt + 1))
    for aid, r in zip(batch, res):
        if r:
            meta[aid] = (r["title"], [a["name"] for a in r.get("authors", [])])


for i in range(0, len(ids), 40):
    (fetch_s2 if SOURCE == "s2" else fetch_arxiv)(ids[i:i + 40])
    time.sleep(3 if SOURCE == "s2" else 10)

print("key\tarxiv\tstatus\ttitle_sim\tbib_first\tarxiv_first\tbib_title\tarxiv_title")
bad = 0
for key, typ, f, ax in recs:
    bt = f.get("title", "")
    if not ax:
        src = f.get("doi") or f.get("url") or f.get("howpublished", "")
        print(f"{key}\t-\tNO_ARXIV\t\t{surname(f.get('author', ''))}\t\t{bt}\t{src}")
        continue
    if ax not in meta:
        print(f"{key}\t{ax}\tNOT_FOUND\t\t\t\t{bt}\t")
        bad += 1
        continue
    at, aa = meta[ax]
    sim = difflib.SequenceMatcher(None, norm(bt), norm(at)).ratio()
    bs = surname(f.get("author", ""))
    as_ = norm(aa[0].split()[-1]) if aa else ""
    ok_t = sim >= 0.85
    ok_a = bs == as_ or bs in norm(aa[0]) or as_ in bs
    status = "OK" if ok_t and ok_a else ("TITLE?" if not ok_t else "AUTHOR?")
    bad += status != "OK"
    print(f"{key}\t{ax}\t{status}\t{sim:.2f}\t{bs}\t{norm(aa[0]) if aa else ''}\t{bt}\t{at}")
print(f"# entries {len(recs)}, with arXiv ID {sum(1 for r in recs if r[3])}, flagged {bad}",
      file=sys.stderr)
