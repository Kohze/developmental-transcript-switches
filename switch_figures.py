"""Build editable review artwork from the accompanying published data."""
from pathlib import Path
from html import escape
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, PathPatch, Rectangle
from matplotlib.path import Path as PlotPath
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "research"
OUT = ROOT / "figures"
INK, MUTED, TEAL, OCHRE = "#182c38", "#435560", "#08726e", "#9d451b"
LIGHT, PALE, DARK = "#dbe3e5", "#faf3e7", "#385d80"
plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":8.3,
    "text.color":INK, "axes.labelcolor":INK, "xtick.color":MUTED, "ytick.color":MUTED,
    "axes.edgecolor":MUTED, "axes.linewidth":.65, "axes.spines.top":False,
    "axes.spines.right":False, "xtick.major.size":3, "ytick.major.size":3,
    "axes.unicode_minus":True, "svg.fonttype":"none", "pdf.fonttype":42,
    "svg.hashsalt":"developmental-switches-figures-v11"})

def export(fig, name):
    for ext, metadata in [("svg", {"Date":None}), ("pdf", {"CreationDate":None})]:
        fig.savefig(OUT / f"{name}.{ext}",metadata=metadata)
    svg = OUT / f"{name}.svg"
    markup = svg.read_text(encoding="utf8")
    descriptions = json.loads((ROOT/"figure_descriptions.json").read_text(encoding="utf8"))
    description = escape(descriptions[name])
    markup = re.sub(r"(<svg\b[^>]*>)", lambda m: m[0]+"\n<desc>"+description+"</desc>",markup,count=1)
    svg.write_text(markup,encoding="utf8")
    plt.close(fig)

def title(fig, x, y, letter, heading):
    fig.text(x,y,letter,fontsize=11,fontweight="bold",va="center")
    fig.text(x+.035,y,heading,fontsize=9.2,fontweight="bold",va="center")

def axes(fig,box):
    return fig.add_axes(box)

def cortical():
    source = pd.read_excel(DATA/"41467_2018_4559_MOESM7_ESM.xlsx",header=2)
    stages = pd.read_excel(DATA/"41467_2018_4559_MOESM10_ESM.xlsx",sheet_name="Dataset S8b",header=2)
    psi = source.iloc[:,9:26].apply(pd.to_numeric,errors="coerce")
    modules = source["Module"]
    sizes = modules.value_counts().sort_index()
    order = source.assign(first=psi.iloc[:,0]).sort_values(["Module","first","Exon ID"]).index
    fig=plt.figure(figsize=(6.6,5.70))
    palette=plt.get_cmap("viridis").copy()
    palette.set_bad("#dcdcdc")
    age_labels=[["E14.5","E16.5","P0","P4","P7","P15","P30","2 mo","21 mo"],
                ["E11","E13","P5","P13","4 wk","6 wk","10 wk","22 mo"]]
    for i,(lo,hi,x,name) in enumerate([(0,9,.09,"Cortex"),(9,17,.555,"Frontal cortex")]):
        title(fig,x,.958,chr(97+i),name)
        ax=axes(fig,[x,.505,.415,.411])
        im=ax.imshow(psi.loc[order].iloc[:,lo:hi],vmin=0,vmax=1,aspect="auto",cmap=palette,
                     interpolation="none",resample=False)
        ax.set_xticks(range(hi-lo),age_labels[i],rotation=50,ha="right",fontsize=8)
        ax.set_yticks(sizes.cumsum()-sizes/2-.5,sizes.index if i==0 else [""]*len(sizes))
        for end in sizes.cumsum()[:-1]:
            ax.axhline(end-.5,lw=.75,color="white")
        ax.tick_params(length=0,pad=3)
    key=axes(fig,[.32,.395,.16,.012])
    fig.colorbar(im,cax=key,orientation="horizontal",ticks=[0,.5,1])
    key.tick_params(labelsize=8,length=2,pad=2)
    fig.text(.09,.401,"Exon inclusion fraction",va="center",fontsize=8)
    fig.add_artist(Rectangle((.56,.395),.017,.014,transform=fig.transFigure,fc="#dcdcdc",ec=MUTED,lw=.4))
    fig.text(.585,.401,"Missing measurement",va="center",fontsize=8)
    title(fig,.055,.30,"c","Endpoint change by module")
    title(fig,.515,.30,"d","Chronological stage 6 (16 samples)")
    paired=psi.iloc[:,[0,8,9,16]].dropna()
    ax=axes(fig,[.105,.115,.325,.145])
    for idx,(early,late,color,marker,name) in enumerate([(0,1,TEAL,"o","Cortex"),(2,3,OCHRE,"s","Frontal")]):
        delta=paired.iloc[:,late]-paired.iloc[:,early]
        for module_index,module in enumerate(sizes.index):
            lo,mid,hi=delta[modules.loc[delta.index]==module].quantile([.25,.5,.75])
            y=module_index+(idx-.5)*.34
            ax.hlines(y,lo,hi,color=color,lw=1.6)
            ax.plot(mid,y,marker,color=color,ms=4,mfc=color if idx==0 else "white")
    ax.axvline(0,c=MUTED,lw=.7,ls=":",zorder=0)
    ax.set(yticks=range(4),yticklabels=sizes.index,ylim=(3.55,-.55),xlabel="Change in inclusion (last − first)")
    ax.set_xlim(-.5,.8);ax.set_xticks([-.5,0,.5])
    handles=[Line2D([],[],c=c,marker=m,mfc=fc,lw=1,label=l,ms=4) for c,m,fc,l in [(TEAL,"o",TEAL,"Cortex"),(OCHRE,"s","white","Frontal")]]
    fig.legend(handles=handles,loc="lower left",bbox_to_anchor=(.075,-.007),ncol=2,frameon=False,fontsize=8)
    ax=axes(fig,[.726,.115,.237,.145])
    groups=stages["Group"].ffill()
    counts=pd.crosstab(groups,stages["Overall"]).reindex(index=groups.unique(),columns=range(1,7)).fillna(0)
    for i,row in enumerate(counts.to_numpy()):
        for j,n in enumerate(row):
            if n:
                ax.text(j,i,str(int(n)),ha="center",va="center",weight="bold")
    for j in range(7):
        ax.axvline(j-.5,color=LIGHT,lw=.65)
    for i in range(5):
        ax.axhline(i-.5,color=LIGHT,lw=.65)
    ax.set(xticks=range(6),xticklabels=range(1,7),yticks=range(4),
           yticklabels=["Sensory receptors","Sensory neurons","Sensory ganglia","Central neurons"],
           xlabel="Cortical reference stage",xlim=(-.5,5.5),ylim=(3.5,-.5))
    for sp in ax.spines.values():sp.set_visible(False)
    ax.tick_params(length=0,labelsize=8)
    export(fig,"cortical")

def diagram_ax(fig, position):
    ax=axes(fig,position)
    ax.set(xlim=(0,100),ylim=(0,100))
    ax.axis("off")
    return ax

def arrow(ax,start,end,color=MUTED):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle="-|>",mutation_scale=8.5,lw=1,color=color))

def text(ax,x,y,label,**kw):
    ax.text(x,y,label,va="center",**kw)

def exon(ax,x,y,width,colour):
    ax.add_patch(Rectangle((x,y-3),width,6,color=colour,lw=.5))

def arc(ax,x1,x2,y,h,colour):
    line=PlotPath([(x1,y),(x1+(x2-x1)*.34,y+h),(x2-(x2-x1)*.34,y+h),(x2,y)],
                  [PlotPath.MOVETO,PlotPath.CURVE4,PlotPath.CURVE4,PlotPath.CURVE4])
    ax.add_patch(PathPatch(line,fill=False,ec=colour,lw=1.4))

def robo():
    fig=plt.figure(figsize=(6.6,5.00))
    title(fig,.04,.961,"a","NOVA favours skipping of the ROBO microexon")
    ax=diagram_ax(fig,[.055,.72,.905,.195])
    ax.plot([2,44],[54,54],c=MUTED,lw=.8)
    for x,w,c in [(2,8,DARK),(22,3,OCHRE),(36,8,DARK)]:exon(ax,x,54,w,c)
    arc(ax,10,22,57,24,OCHRE);arc(ax,25,36,57,24,OCHRE);arc(ax,10,36,51,-26,TEAL)
    text(ax,23,92,"Include 6b",ha="center",color=OCHRE)
    text(ax,23,10,"Skip 6b",ha="center",color=TEAL)
    text(ax,50,69,"6b encodes a linker between Ig3 and Ig4.")
    text(ax,50,37,"The included ROBO1 form produces a\nstronger repulsive response in the assay.")
    for panel,src,box,head,labs,embryos,colour,xlab in [
            ("b",4,[.255,.415,.525,.21],"Crossing at E12.5 in Nova1/2 double knockouts",
             ["Wild type","Double knockout","KO + Robo1 edit","KO + Robo2 edit","KO + both edits"],
             [7,4,6,6,7],TEAL,"Contralateral / ipsilateral signal, relative to wild type"),
            ("c",7,[.255,.09,.525,.16],"Lumbar commissure at E10.5 with intact NOVA",
             ["Wild type","Robo1 deletion","Robo2 deletion","Double deletion"],
             [10,8,6,6],OCHRE,"Commissure / floor-plate thickness")]:
        title(fig,.04,box[1]+box[3]+.06,panel,head)
        sheet=pd.read_excel(DATA/f"elife-46042-fig{src}-data1-v1.xlsx",header=None)
        end=sheet.index[sheet[0].astype(str).str.lower()=="average"][0]
        mean=sheet.iloc[end,1:].to_numpy(float)
        sd=sheet.iloc[end+1,1:].to_numpy(float)
        observations=sheet.iloc[5 if src==4 else 3:end,1:].apply(pd.to_numeric,errors="coerce")
        ax=axes(fig,box)
        for i,(m,s) in enumerate(zip(mean,sd)):
            ax.errorbar(m,i,xerr=s,fmt="o",color=colour,ms=4.8,capsize=2.5,lw=1.4)
            ax.text(1.12,i,str(embryos[i]),transform=ax.get_yaxis_transform(),ha="center",va="center")
            ax.text(1.31,i,str(observations.iloc[:,i].count()),transform=ax.get_yaxis_transform(),ha="center",va="center")
        for x,v in [(1.12,"Embryos"),(1.31,"Readings")]:
            ax.text(x,1.045,v,transform=ax.transAxes,ha="center",fontsize=8,weight="bold")
        ax.set(yticks=range(len(labs)),yticklabels=labs,ylim=(len(labs)-.5,-.55),xlabel=xlab)
        ax.tick_params(axis="y",length=0)
        ax.set_xlim((.25,1.22) if src==4 else (0,.55))
        if src==4:ax.axvline(1,lw=.7,ls=":",color=MUTED)
        ax.grid(axis="x",color=LIGHT,lw=.65);ax.set_axisbelow(True)
    export(fig,"robo")

def routes():
    fig=plt.figure(figsize=(6.6,6.2))
    for i,(letter,heading) in enumerate([("a","Axon guidance  ·  translation at the floor plate"),
            ("b","Cardiac mechanics  ·  RBM20 represses titin spring exons"),
            ("c","Germ-cell splicing  ·  poison-exon inclusion limits TRA2B dosage"),
            ("d","Neural stem-cell niche  ·  two cells supply different DLK1 forms")]):
        top=.97-i*.246
        title(fig,.04,top,letter,heading)
        ax=diagram_ax(fig,[.055,top-.174,.91,.143])
        if i==0:
            ax.plot([1,25],[64,64],color=MUTED,lw=1)
            for x,w,c in [(1,7,DARK),(8,10,OCHRE),(18,7,DARK)]:exon(ax,x,64,w,c)
            text(ax,1,40,"Axonal Robo3.2 RNA",weight="bold")
            text(ax,13,91,"Intron 26",ha="center")
            arrow(ax,(13,85),(13,67),MUTED)
            text(ax,36,87,"Floor-plate cue")
            arrow(ax,(47,78),(47,64),TEAL)
            arrow(ax,(26,60),(34,54))
            text(ax,35,51,"Local translation",weight="bold")
            arrow(ax,(58,52),(66,72));arrow(ax,(58,50),(66,28))
            text(ax,67,75,"ROBO3.2 protein")
            text(ax,67,26,"RNA decay via NMD")
        elif i==1:
            text(ax,1,88,"RBM20 transcripts",weight="bold")
            text(ax,1,57,"Canonical start")
            text(ax,1,27,"Alternative start")
            for y,x0 in [(57,20),(27,23)]:
                ax.plot([x0,29],[y,y],color=MUTED,lw=.8)
                exon(ax,x0,y,2.8,DARK)
                exon(ax,27,y,3,TEAL)
            
            arrow(ax,(30,57),(35,47));arrow(ax,(30,27),(35,40))
            text(ax,36,45,"RBM20\nactivity",weight="bold",ha="left")
            arrow(ax,(47,47),(54,64));arrow(ax,(47,41),(54,24))
            text(ax,55,92,"Spring exons",weight="bold");text(ax,55,68,"More skipped");text(ax,55,23,"More included")
            for y,length,turns,descriptor in [(68,7,4,"N2B"),(23,12,7,"N2BA")]:
                x=np.linspace(75,75+length,turns*18)
                ax.plot(x,y+3.7*np.sin(np.linspace(0,2*np.pi*turns,len(x))),color=DARK,lw=1.15)
                text(ax,89,y,descriptor,weight="bold")
        elif i==2:
            text(ax,1,74,"Tra2b precursor",weight="bold")
            ax.plot([1,25],[48,48],c=MUTED,lw=.8)
            for x,w,c in [(1,6,DARK),(11,4,OCHRE),(19,6,DARK)]:exon(ax,x,48,w,c)
            arc(ax,7,19,45,-16,TEAL)
            arrow(ax,(26,49),(34,70));arrow(ax,(26,46),(34,27))
            text(ax,35,72,"Include poison exon");text(ax,35,25,"Skip poison exon")
            arrow(ax,(61,72),(67,72));arrow(ax,(61,25),(67,25))
            text(ax,68,72,"Unproductive RNA")
            text(ax,68,25,"TRA2B protein")
        else:
            text(ax,1,86,"Niche astrocyte",weight="bold")
            text(ax,1,59,"Cleavable DLK1")
            arrow(ax,(24,59),(33,59),TEAL)
            text(ax,34,59,"Soluble DLK1",color=TEAL)
            text(ax,34,24,"Membrane-bound DLK1",color=DARK)
            text(ax,1,24,"Neural stem cell",weight="bold")
            arrow(ax,(55,59),(69,49),TEAL)
            arrow(ax,(64,24),(69,39),DARK)
            text(ax,71,44,"More\nneurospheres",weight="bold")
        findings = ["UPF2 loss increases postcrossing ROBO3.2 protein in axons.",
                    "Fetal rat cardiomyocytes with longer titin develop less passive tension.",
                    "Poison-exon deletion disrupts meiotic prophase in mouse germ cells.",
                    "Restoring the appropriate form in each cell type rescues the response."]
        fig.text(.055,top-.199,"Readout",fontsize=8.1,weight="bold")
        fig.text(.164,top-.199,findings[i],fontsize=8.1)
        if i<3:fig.add_artist(Line2D([.04,.96],[top-.218]*2,transform=fig.transFigure,color=LIGHT,lw=.8))
    export(fig,"routes")

