"""Check Matplotlib artists against workbooks and the delivered artwork against the manuscript."""
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymupdf
from matplotlib.colors import to_rgba

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
import switch_figures as plots
import figure_comparisons as comparisons

proof={}
def capture(fig,name):
    proof[name]=fig

plots.export=comparisons.export=capture
for make in [plots.cortical,plots.robo,plots.routes,comparisons.snap25,comparisons.fruitless,comparisons.timing]:
    make()

data=root/"research"
events=pd.read_excel(next(data.glob("*ESM7*")),header=2)
m=events.iloc[:,9:26].apply(pd.to_numeric,errors="coerce")
order=events.assign(first=m.iloc[:,0]).sort_values(["Module","first","Exon ID"]).index
cortex,frontal,bar,changes,stage=proof["cortical"].axes
for ax,values in [(cortex,m.iloc[:,0:9]),(frontal,m.iloc[:,9:17])]:
    np.testing.assert_allclose(ax.images[0].get_array().filled(np.nan),values.loc[order],equal_nan=True)
ends=m.iloc[:,[0,8,9,16]].dropna()
assert list(ends.groupby(events.Module).size())==[979,938,336,324]
for side,(lo,hi) in enumerate([(0,1),(2,3)]):
    delta=ends.iloc[:,hi]-ends.iloc[:,lo]
    for i,(_,series) in enumerate(delta.groupby(events.Module)):
        q=series.quantile([.25,.5,.75])
        idx=4*side+i
        np.testing.assert_allclose(changes.collections[idx].get_segments()[0][:,0],q.iloc[[0,2]])
        np.testing.assert_allclose(changes.lines[idx].get_xdata(),[q.iloc[1]])
assert [t.get_text() for t in stage.texts]==["3","2","2","5","4"]
for ax,panel,embryos,first in zip(proof["robo"].axes[1:],[4,7],[[7,4,6,6,7],[10,8,6,6]],[5,3]):
    m=pd.read_excel(next(data.glob(f"elife-46042-fig{panel}*")),header=None)
    n=m.index[m[0].astype(str).str.lower().eq("average")][0]
    readings=m.iloc[first:n,1:].apply(pd.to_numeric,errors="coerce")
    for i,container in enumerate(ax.containers):
        avg=readings.iloc[:,i].mean()
        sd=readings.iloc[:,i].std(ddof=1 if panel==4 else 0)
        np.testing.assert_allclose(container.lines[0].get_xdata(orig=False),[avg])
        np.testing.assert_allclose(container.lines[2][0].get_segments()[0][:,0],[avg-sd,avg+sd])
        assert int(ax.texts[2*i].get_text())==embryos[i]
        assert int(ax.texts[2*i+1].get_text())==readings.iloc[:,i].count()
source=pd.read_csv(root/"figures/data/snap25.csv")
for (panel,rows),ax in zip(source.groupby("panel"),proof["snap25"].axes):
    for row,con in zip(rows.itertuples(),ax.containers,strict=True):
        np.testing.assert_allclose(con.lines[0].get_xdata(orig=False),[row.mean_percent])
        if pd.isna(row.sem_percent):
            assert not con.lines[2]
        else:
            np.testing.assert_allclose(con.lines[2][0].get_segments()[0][:,0],
                                      [row.mean_percent-row.sem_percent,row.mean_percent+row.sem_percent])
sheet=pd.read_excel(next(data.glob("*59224*")),header=None)
distribution,counts,timeline=proof["fruitless"].axes
assert [list(zip(line.get_xdata(),line.get_ydata())) for line in timeline.lines] == [[(4,1)],[(2,0)],[(1,0)]]
assert [tick.get_text() for tick in timeline.get_xticklabels()] == ["L1","L2","L3","L4"]
for ax in (distribution, counts):
    assert ax.get_xlabel() == "Two-day knockdown window"
    assert [tick.get_text() for tick in ax.get_xticklabels() if tick.get_visible()] == list("123456789")
for i in range(9):
    xy=distribution.collections[2*i].get_offsets()
    np.testing.assert_allclose(xy[:,1],sheet.iloc[2:,3+i].astype(float))
    assert len(xy)==24 and max(abs(xy[:,0]-i-1))<.44
    np.testing.assert_allclose(distribution.collections[2*i+1].get_segments()[0][:,1],np.median(np.asarray(xy[:,1],dtype=float)))
    fills=counts.collections[i].get_facecolors()
    assert len(fills)==24 and (fills==to_rgba(plots.INK)).all(axis=1).sum()==int(str(sheet.iloc[2,13+i]).split()[0])
for i in range(2):
    upper,lower=proof["timing"].axes[i*2:i*2+2]
    a,b=[l.get_ydata() for l in upper.lines]
    diff=lower.collections[-1].get_offsets()[:,1]
    np.testing.assert_allclose(abs(a-b),diff)
    np.testing.assert_allclose(diff,[0,0,.6,0,0])

descriptions=json.loads((root/"figure_descriptions.json").read_text())
doc=pymupdf.open(root/"Developmental_transcript_switches.pdf")
report={}
for key,figure in proof.items():
    source_pdf=pymupdf.open(root/f"figures/{key}.pdf")
    page=source_pdf[0]
    fonts=page.get_fonts()
    assert fonts and all(x[1]=="ttf" and source_pdf.extract_font(x[0])[3] for x in fonts)
    assert all(page.rect.contains(pymupdf.Rect(*w[:4])) for w in page.get_text("words"))
    xml=ElementTree.parse(root/f"figures/{key}.svg")
    assert xml.find("{*}desc").text==descriptions[key] and len(xml.findall(".//{*}text"))>10
    matching=[p for p in doc if any(key+'.pdf' in str(x) for x in p.get_xobjects())]
    number=list(proof).index(key)+1
    if not matching:
        matching=[p for p in doc if re.search(rf"Fig\.? {number}\.",p.get_text())]
    assert len(matching)==1
    manuscript_page=matching[0]
    spans=[s for block in manuscript_page.get_text("dict")["blocks"] for line in block.get("lines",[])
           for s in line["spans"] if "DejaVuSans" in s["font"]]
    minimum=min(s["size"] for s in spans)
    assert minimum>=7.5
    assert bool(page.get_images())==(key=="cortical")
    report[key]=dict(manuscript_page=manuscript_page.number+1,minimum_print_points=round(minimum,2),
                     embedded_font_faces=len(fonts),svg_text_elements=len(xml.findall(".//{*}text")))
    source_pdf.close()
    plt.close(figure)
(root/"qa/figure_checks.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report))

