"""Genotype comparisons, timed perturbation and constructed trajectories."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from switch_figures import DATA, OUT, INK, MUTED, TEAL, OCHRE, DARK, LIGHT, PALE, axes, export, title


def snap25():
    data = pd.read_csv(OUT / "data/snap25.csv")
    fig=plt.figure(figsize=(6.6,3.95))
    handles=[Line2D([],[],marker=m,ls="",color=c,mfc=fc,ms=5.5,label=l)
             for m,c,fc,l in [("o",TEAL,TEAL,"Cassette retained"),("s",OCHRE,"white","Cassette excised")]]
    fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.55,1.01),ncol=2,frameon=False)
    for panel,heading,measures,box,xlabel in [
        ("A","Which exon 5 product is present?",["Wild type","Heterozygote","Homozygote"],
         [.228,.582,.705,.222],"Exon 5a share of 5a + 5b RNA (%)"),
        ("B","How much RNA and protein remain?",["Total RNA","Total protein"],
         [.228,.12,.705,.168],"Homozygote abundance (% of line-matched wild type)")]:
        title(fig,.045,box[1]+box[3]+.052,panel.lower(),heading)
        ax=axes(fig,box)
        for row in data[data.panel==panel].itertuples():
            retained=row.line=="Retained"
            y=measures.index(row.measure)+(-.15 if retained else .15)
            colour=TEAL if retained else OCHRE
            ax.errorbar(row.mean_percent,y,xerr=None if pd.isna(row.sem_percent) else row.sem_percent,
                        fmt="o" if retained else "s",ms=5.4,mfc=colour if retained else "white",
                        mew=1.1,color=colour,elinewidth=1.3,capsize=2.4)
        ax.set(yticks=range(len(measures)),yticklabels=measures,ylim=(len(measures)-.45,-.6),
               xlabel=xlabel)
        ax.tick_params(axis="y",length=0)
        ax.set_xlim((0,104) if panel=="A" else (0,130))
        ax.set_xticks([0,25,50,75,100] if panel=="A" else [0,25,50,75,100,125])
        ax.grid(axis="x",color=LIGHT,zorder=0,lw=.65);ax.set_axisbelow(True)
        if panel=="B":
            ax.axvline(100,ls=":",color=INK,lw=1.1)
            for r in data[(data.panel=="B") & (data.measure=="Total protein")].itertuples():
                retained=r.line=="Retained"
                ax.annotate(f"{r.mean_percent:.1f}%",(r.mean_percent+(-r.sem_percent if retained else r.sem_percent),1+(-.15 if retained else .15)),
                            xytext=(-4 if retained else 4,0),textcoords="offset points",
                            ha="right" if retained else "left",va="center",fontsize=8)
            ax.text(100,-.63,"WT",ha="center",va="bottom",fontsize=8)
    export(fig,"snap25")


def swarm_x(ax, stage, observations, diameter):
    """Pack dots at their observed y values. Separation is measured in display pixels."""
    xp=ax.transData.transform((stage,0))[0]
    yp=ax.transData.transform(np.column_stack([np.full(len(observations),stage),observations]))[:,1]
    placed=[]
    result=np.empty(len(observations))
    for idx in np.argsort(yp,kind="stable"):
        y=yp[idx]
        nearby=[(x,v) for x,v in placed if abs(y-v)<diameter]
        candidates=[xp]
        for x,v in nearby:
            dx=np.sqrt(max(0,diameter**2-(v-y)**2))
            candidates.extend([x-dx,x+dx])
        x=next(x for x in sorted(candidates,key=lambda x:abs(x-xp))
               if all((x-a)**2+(y-b)**2>=diameter**2-1e-6 for a,b in nearby))
        result[idx]=ax.transData.inverted().transform((x,y))[0]
        placed.append((x,y))
    return result


def fruitless():
    source=pd.read_excel(DATA/"elife-59224-fig1-data1-v2.xlsx",header=None)
    obs=source.iloc[2:,3:12].to_numpy(float)
    stages=np.arange(1,10)
    mated=[int(str(cell).split()[0]) for cell in source.iloc[2,13:22]]
    fig=plt.figure(figsize=(6.6,6.05))
    title(fig,.035,.963,"a","Time spent courting a female in adulthood (fly)")
    ax=axes(fig,[.12,.628,.85,.263])
    ax.set(xlim=(.5,9.5),ylim=(-6,107),yticks=[0,25,50,75,100],ylabel="Courtship index (%)",xticks=stages)
    ax.set_xlabel("Two-day knockdown window")
    ax.tick_params(axis="x",labelbottom=True,length=3,pad=2)
    ax.axvspan(4.5,5.5,color=PALE,zorder=-2)
    ax.text(.51,1.032,"Median bar   ·   24 males per cohort",ha="left",transform=ax.get_xaxis_transform(),fontsize=8)
    ax.text(5,1.02,"Pupation",ha="center",va="bottom",transform=ax.get_xaxis_transform(),fontsize=8.2,weight="bold")
    fig.canvas.draw()
    for s,v in zip(stages,obs.T):
        x=swarm_x(ax,s,v,2.85*fig.dpi/72)
        assert np.max(abs(x-s)) < .44
        ax.scatter(x,v,s=6.4,c=OCHRE if s==5 else TEAL,edgecolors="none")
        ax.hlines(np.median(v),s-.34,s+.34,color=INK,lw=1.2)
    title(fig,.035,.512,"b","Number mating in each cohort")
    ax=axes(fig,[.12,.359,.85,.105]);ax.set_xlim(.5,9.5);ax.set_ylim(-.65,4.4)
    ax.axvspan(4.5,5.5,color=PALE,zorder=-2)
    for s,n in zip(stages,mated):
        x=s+((np.arange(24)%6)-2.5)*.101
        y=np.arange(24)//6
        ax.scatter(x,y,marker="s",s=10.2,c=[INK if i<n else "white" for i in range(24)],
                   edgecolors=INK,linewidths=.44)
        ax.text(s,4.35,str(n),ha="center",va="bottom",fontsize=8.3,weight="bold")
    ax.set(yticks=[],xticks=stages,xlabel="Two-day knockdown window")
    for sp in ["left","right","top"]:ax.spines[sp].set_visible(False)
    fig.text(.12,.260,"One square per male. Filled squares denote mating.",fontsize=8)
    title(fig,.035,.212,"c","Timing of epidermal seam cell fusion in the nematode")
    timeline = axes(fig,[.319,.069,.612,.105])
    for row in (0,1):
        timeline.hlines(row,1,4,color=LIGHT,lw=1.1,zorder=0)
    timeline.plot(4,1,"o",color=TEAL,ms=6)
    timeline.plot(2,0,"o",color=TEAL,ms=6)
    timeline.plot(1,0,marker="^",mfc="white",mec=INK,ms=6)
    timeline.set(xlim=(.87,4.13),ylim=(-.45,1.45),xticks=[1,2,3,4],
                 xticklabels=["L1","L2","L3","L4"],yticks=[0,1],
                 yticklabels=["Early LIN-29a or LIN-29b","Endogenous expression"])
    timeline.tick_params(length=0,pad=4)
    for spine in timeline.spines.values():
        spine.set_visible(False)
    fig.text(.035,.014,"Triangle: early expression begins. Circle: fusion observed. L1–L4: larval stages.",fontsize=8)
    export(fig,"fruitless")


def timing():
    histories=[([.2,.2,.8,.8,.8],[.2,.2,.2,.8,.8]),([.2,.2,.8,.2,.2],[.2]*5)]
    fig=plt.figure(figsize=(6.6,3.74))
    for i,((a,b),x,heading) in enumerate(zip(histories,[.113,.594],["Delayed replacement","Reversible excursion"])):
        title(fig,x-.066,.955,chr(97+i),heading)
        age=np.arange(1,6)
        ax=axes(fig,[x,.465,.365,.338])
        for y,color,marker,style,size in [(a,TEAL,"o","-",6.3),(b,OCHRE,"s","--",3.1)]:
            ax.plot(age,y,style,marker=marker,color=color,mfc="white",ms=size,mew=1.2,lw=1.5)
        ax.set(ylim=(0,1),yticks=[0,.2,.5,.8,1],xlim=(.8,5.2),xticks=age)
        ax.tick_params(axis="x",labelbottom=False)
        if i==0:ax.set_ylabel("Transcript A fraction")
        for side in ["right","top"]:ax.spines[side].set_visible(False)
        delta=abs(np.subtract(a,b))
        lower=axes(fig,[x,.157,.365,.133])
        lower.vlines(age,0,delta,color=DARK,lw=1.8)
        lower.scatter(age,delta,color=DARK,s=16,zorder=3)
        lower.set(ylim=(-.04,.7),yticks=[0,.6],xlim=(.8,5.2),xticks=age,xlabel="Sampled age")
        if i==0:lower.set_ylabel("|Difference|",fontsize=8)
    fig.text(.50,.365,"Both histories give the same absolute regional difference",ha="center",fontsize=8.3,weight="bold")
    handles=[Line2D([],[],ls=ls,marker=mk,color=c,ms=ms,mfc="white",label=l)
             for ls,mk,c,ms,l in [("-","o",TEAL,6,"Region 1"),("--","s",OCHRE,3.5,"Region 2")]]
    fig.text(.115,.863,"Constructed examples",fontsize=8,color=MUTED)
    fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.69,.911),ncol=2,frameon=False,borderaxespad=0)
    export(fig,"timing")

