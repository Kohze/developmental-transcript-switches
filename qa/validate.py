"""Validate the manuscript build and recompute analytical examples from their definitions."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import math
import re

import unicodedata
import numpy as np
import pandas as pd
import pymupdf
from bs4 import BeautifulSoup

root = Path(__file__).resolve().parent.parent
def read(name):
    return (root / name).read_text(encoding="utf-8")
def rows(name):
    return list(csv.DictReader(read("figures/data/" + name + ".csv").splitlines()))
def near(a, b):
    assert math.isclose(float(a), float(b), abs_tol=1e-9), (a,b)

source = read("manuscript.md")
html = BeautifulSoup(read("Developmental_transcript_switches.html"), "html.parser")
pdf = pymupdf.open(root / "Developmental_transcript_switches.pdf")
keys = json.loads(read("qa/citation_order.json"))
records = {r["key"]:r for r in json.loads(read("research/source_registry.json"))}
assert set(keys) == set(records) == set(re.findall(r"@(\w+)", source + read("figure_legends.json")))
assert set(keys) == set(re.findall(r"@(?:article|inproceedings|phdthesis|misc)\{(\w+),",read("references.bib")))
ids = Counter(x["id"] for x in html.select("[id]"))
assert all(n == 1 for n in ids.values())
assert all(a["href"][1:] in ids for a in html.select('a[href^="#"]'))
assert len(html.select(".references p")) == len(keys)
for i,key in enumerate(keys,1):
    assert html.select_one(f"#ref-{i} a")["href"] == records[key]["source_url"]
    assert html.select_one(f'a[href="#ref-{i}"]')
assert not html.select("script[src],img[src],link[rel=stylesheet]")
assert not re.search(r"\[@|\{\{|\ufffd|\?\?|\w\?\w",html.get_text(" "))
for label in ("Figure","Table"):
    mentions = re.findall(rf"{label} (\d+)",source)
    captions = html.select("figcaption" if label=="Figure" else "caption")
    assert set(mentions)=={str(i) for i in range(1,len(captions)+1)}
    assert all(c.get_text().startswith(f"{label} {i}.") for i,c in enumerate(captions,1))
for page in pdf:
    words = page.get_text("words")
    assert len(words)>50
    assert all(0<=x0<x1<=page.rect.width+1 and 0<=y0<y1<=page.rect.height+1 for x0,y0,x1,y1,*_ in words)
links = {link.get("uri","").lower() for page in pdf for link in page.get_links()}
assert all(r["source_url"].lower() in links for r in records.values())
def normal(value):
    return " ".join(unicodedata.normalize("NFKC", value).replace("-\\n","").split())

text = normal(" ".join(page.get_text() for page in pdf))
for figure in range(1, len(html.select("figure"))+1):
    assert f"Fig. {figure}." in text or f"Fig {figure}." in text
for heading in html.select("h1,h2,h3"):
    assert normal(heading.get_text()) in text, heading.get_text()
assert "Keywords:" in pdf[0].get_text() and "Introduction" in pdf[1].get_text()
assert abs(pdf[0].rect.width - 595.28) < .1
assert len(html.select("figure svg"))==6
assert "Missing character" not in read("qa/compile.log")
assert "Overfull" not in read("qa/compile.log")
for figure in re.findall(r"!\\[(\\w+)\\]",source):
    assert len(pymupdf.open(root / f"figures/{figure}.pdf"))==1
    assert (root / f"figures/{figure}.svg").stat().st_size>1000

data=root/"research"
m=pd.read_excel(next(data.glob("*ESM7*")),header=2)
assert list(m.groupby("Module").size()) == [1118,1027,385,353]
psi=m.iloc[:,9:26].apply(pd.to_numeric,errors="coerce")
assert psi.isna().sum().sum()==1277 and psi.stack().between(0,1).all()
stages=pd.read_excel(next(data.glob("*ESM10*")),sheet_name="Dataset S8b",header=2)
assert stages["True Stage"].eq(6).all() and len(stages)==16
assert stages.groupby(stages["Group"].ffill(),sort=False)["Overall"].apply(list).map(sorted).tolist()==[[1,1,1],[1,1,2,2],[6]*5,[6]*4]
for panel,first,ddof,means in [(4,5,1,[1,.52,.77,.52,.84]),(7,3,0,[.21,.40,.22,.41])]:
    m=pd.read_excel(next(data.glob(f"elife-46042-fig{panel}*")),header=None)
    last=m.index[m[0].astype(str).str.lower().eq("average")][0]
    observations=m.iloc[first:last,1:].apply(pd.to_numeric,errors="coerce")
    np.testing.assert_allclose(observations.mean(),m.iloc[last,1:].astype(float),atol=1e-9)
    np.testing.assert_allclose(observations.std(ddof=ddof),m.iloc[last+1,1:].astype(float),atol=1e-9)
    assert observations.mean().round(2).tolist()==means
m=pd.read_excel(next(data.glob("*59224*")),header=None)
v=m.iloc[2:,3:12].astype(float)
assert v.count().tolist()==[24]*9 and v.median().tolist()==[91.5,95,92,60,7,67,94,92,89]
assert m.iloc[2,13:22].tolist()==[f"{i} out of 24" for i in [20,21,19,3,0,5,12,23,18]]
# Published means and SEMs transcribed from Johansson et al., figures 1 and 2.
measurements = rows("snap25")
assert len(measurements) == 10
expected = [(16.7,1.9),(17.5,1.2),(51.6,1.7),(68.9,2.1),(100,None),(100,None),
            (55.5,2.7),(117.3,6.8),(80.7,3.6),(110.9,2.3)]
for row,(mean,sem) in zip(measurements,expected):
    near(row["mean_percent"],mean)
    if sem is None:
        assert row["sem_percent"] == ""
    else:
        near(row["sem_percent"],sem)
    assert int(row["mice_per_genotype"]) == (5 if row["panel"]=="A" else 6)
for a,b in [([.2,.2,.8,.8,.8],[.2,.2,.2,.8,.8]),([.2,.2,.8,.2,.2],[.2]*5)]:
    np.testing.assert_allclose(np.abs(np.subtract(a,b)),[0,0,.6,0,0])
result=dict(pages=len(pdf),references=len(keys),abstract_words=len(source.split("## Abstract\n\n",1)[1].split("\n\n",1)[0].split()),
            vector_figures=len(html.select("figure svg")),tables=len(html.select("table")),
            manuscript_sha256=hashlib.sha256((root/"manuscript.md").read_bytes()).hexdigest(),
            pdf_sha256=hashlib.sha256((root/"Developmental_transcript_switches.pdf").read_bytes()).hexdigest())
(root/"qa/validation.json").write_text(json.dumps(result,indent=2),encoding="utf8")
print(result)

