"""Build the LaTeX, PDF, accessible HTML and bibliography from the review sources."""
from pathlib import Path
import re, json, html, os, shutil, subprocess
from pypdf import PdfReader
from switch_figures import cortical, robo, routes
from figure_comparisons import snap25, fruitless, timing

P=Path(__file__).resolve().parent
QA=P/"qa"
QA.mkdir(exist_ok=True)
OUT=P/"Developmental_transcript_switches.pdf"
HTML=OUT.with_suffix(".html")
source=(P/"manuscript.md").read_text(encoding="utf8").strip().split("\n\n")
TITLE=source[0].removeprefix("# ")
BYLINE=source[1].split(": ",1)[1]
byline_html = "<br>".join(html.escape(line.strip()) for line in BYLINE.splitlines())
byline_html = re.sub(r"&lt;sup&gt;([0-9,]+)&lt;/sup&gt;", r"<sup>\1</sup>", byline_html)
DATE=source[2].removeprefix("Date: ")
assert source[3]=="## Abstract"
ABSTRACT=source[4]
KEYWORDS=source[5].removeprefix("Keywords: ")
legends=json.loads((P/"figure_legends.json").read_text(encoding="utf8"))
FIGURES={key:(None,value) for key,value in legends.items()}
TABLES = {}
BLOCKS = []
for paragraph in source[6:]:
    if paragraph.startswith('### '):
        BLOCKS.append(('h2', paragraph[4:]))
    elif paragraph.startswith('## '):
        BLOCKS.append(('h1', paragraph[3:]))
    elif re.match(r'^Table \d+\. .*\n\|', paragraph):
        caption, header, separator, *rows = paragraph.splitlines()
        cells = lambda row: [v.strip() for v in row.strip('|').split('|')]
        assert len(cells(separator)) == 3 and all(len(cells(row)) == 3 for row in rows)
        key = 'prediction_tasks'
        TABLES[key] = dict(caption=caption, headers=cells(header), rows=[cells(row) for row in rows], widths=[118,155,195])
        BLOCKS.append(('table', key))
    elif paragraph.startswith('!['):
        key = re.fullmatch(r'!\[(\w+)\]\(figures/\1\.svg\)', paragraph).group(1)
        BLOCKS.append(('figure', key))
    else:
        BLOCKS.append(('p', paragraph))
figure_count=table_count=0
for kind,t in BLOCKS:
    if kind=='figure':
        figure_count+=1
        factory,caption=FIGURES[t]
        FIGURES[t]=(factory,re.sub(r'^Figure \d+\.',f'Figure {figure_count}.',caption))
    elif kind=='table':
        table_count+=1
        TABLES[t]['caption']=re.sub(r'^Table \d+\.',f'Table {table_count}.',TABLES[t]['caption'])
assert figure_count==len(FIGURES) and table_count==len(TABLES)

def clean(t):
    t=re.sub('<[^>]*>','',html.unescape(str(t)))
    t=t.translate(str.maketrans({'–':'-','—':'-','‑':'-','‘':"'",'’':"'",'“':'"','”':'"','\xa0':' '}))
    t=t.replace('_i','ᵢ').replace('_j','ⱼ')
    return t

REG={x['key']:x for x in json.loads((P/'research/source_registry.json').read_text(encoding='utf-8'))}
CITE_RE=re.compile(r'\[(@[^\]]+)\]')
KEYS=[]
def record(t):
    for m in CITE_RE.finditer(t):
        for key in re.findall(r'@([A-Za-z0-9]+)',m.group(1)):
            if key not in KEYS: KEYS.append(key)
for kind,t in BLOCKS:
    if kind=='table':
        d=TABLES[t];record(d['caption'])
        for row in d['rows']:
            for v in row:record(v)
    elif kind=='figure':record(FIGURES[t][1])
    else:record(t)
assert all(REG[k].get('matched') for k in KEYS)
assert len({REG[k]['source_url'].lower() for k in KEYS})==len(KEYS)
NUM={k:i+1 for i,k in enumerate(KEYS)}

def rich(t,web=False):
    t=html.escape(clean(t))
    t=re.sub(r'\*([^*\n]+)\*', r'<i>\1</i>', t)
    def cites(m):
        out=[]
        for k in re.findall(r'@([A-Za-z0-9]+)',m.group(1)):
            dest=('#ref-'+str(NUM[k])) if web else REG[k]['source_url']
            col='' if web else ' color="#1F6576"'
            out.append(f'<a href="{dest}"{col}>{NUM[k]}</a>')
        return '['+', '.join(out)+']'
    t=CITE_RE.sub(cites,t)
    t=re.sub(r'\[([^]\n]+)\]\((https://[^\s)]+)\)', r'<a href="\2">\1</a>', t)
    t=re.sub(r'\{\{([^|{}]+)\|([^{}]+)\}\}',lambda m:f'<a href="{m[2]}"'+('' if web else ' color="#1F6576"')+'>'+m[1]+'</a>',t)
    return t.replace('\n','<br/>')

def authors(r):
    a=r.get('author_list',[])
    names=[]
    for x in a:
        if x.get('collectiveName'): name=x['collectiveName']
        elif x.get('lastName'):
            initials=x.get('initials') or ''.join(w[0] for w in x.get('firstName','').split() if w)
            name=x['lastName']+' '+initials
        else:name=x.get('fullName','')
        if name:names.append(clean(name))
    return ', '.join(names[:3])+(' et al.' if len(names)>3 else '') if names else clean(r.get('authors',''))
def reftext(k):
    r=REG[k]
    loc=clean(r.get('journal','')).rstrip('.')+'. '+str(r['year'])
    if r.get('volume'):loc+=';'+str(r['volume'])
    if r.get('pages'):loc+=':'+str(r['pages'])
    note=(' '+r['version_note']) if r.get('version_note') else ''
    return clean(f"[{NUM[k]}] {authors(r).rstrip('.')}. {r['title'].rstrip('.')}. {loc}.{note}")

for generate in (cortical, robo, routes, snap25, fruitless, timing):
    generate()

parts=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',f'<title>{html.escape(TITLE)}</title>',
'''<style>body{max-width:830px;margin:42px auto;padding:0 24px;color:#17252d;font:18px/1.58 Georgia,"Times New Roman",serif}h1{font-size:2rem;line-height:1.22}h2{font-size:1.4rem;line-height:1.3;margin-top:2.1rem}h3{font-size:1.1rem;margin-top:1.5rem}a{color:#146378}p{margin:.6rem 0 1rem}small{font-size:.82rem}figure{margin:1.8rem 0}svg{width:100%;height:auto}figcaption{font-size:.88rem;line-height:1.5;margin-top:.5rem}table{width:100%;border-collapse:collapse;font-size:.86rem;line-height:1.4;margin:1.5rem 0}caption{text-align:left;font-weight:bold;margin-bottom:.6rem}td,th{border:1px solid #cfd8dc;padding:15px 11px;text-align:left;vertical-align:top}th{background:#17313f;color:#fff}tbody tr:nth-child(odd){background:#f3f6f7}.references p{font-size:.88rem;overflow-wrap:anywhere}nav{padding:16px 20px;background:#f3f6f7}nav a{display:block;font-size:.9rem;margin:.15rem 0}details summary{cursor:pointer;font-weight:bold} @media print{body{margin:0;max-width:none;font-size:11.5pt}h2,h3{break-after:avoid}figure,tr{break-inside:avoid}nav{display:none}}</style></head><body><article>''',
f'<header style="text-align:center"><h1>{html.escape(TITLE)}</h1><p>{byline_html}</p><p>{DATE}</p></header><h2>Abstract</h2><p>{rich(ABSTRACT,True)}</p><p><strong>Keywords:</strong> {html.escape(KEYWORDS)}</p>' ]
heads=[t for k,t in BLOCKS if k=='h1']
parts.append('<nav aria-label="Review contents"><details><summary>Review contents</summary>'+''.join(f'<a href="#section-{i}">{html.escape(t)}</a>' for i,t in enumerate(heads,1))+'</details></nav>')
n=0
for kind,t in BLOCKS:
    if kind=='p':parts.append('<p>'+rich(t,True)+'</p>')
    elif kind in ['h1','h2']:
        if kind=='h1':n+=1;parts.append(f'<h2 id="section-{n}">{html.escape(t)}</h2>')
        else:parts.append('<h3>'+html.escape(t)+'</h3>')
    elif kind=='figure':
        svg=(P/'figures'/(t+'.svg')).read_text(encoding='utf-8');svg=svg[svg.index('<svg'):]
        for old in set(re.findall(r'\bid="([^"]+)"',svg)):
            new=t+'-'+old
            svg=svg.replace('id="'+old+'"','id="'+new+'"').replace('url(#'+old+')','url(#'+new+')').replace('href="#'+old+'"','href="#'+new+'"')
        alt=json.loads((P/"figure_descriptions.json").read_text(encoding="utf8"))[t]
        svg=re.sub('<svg ', '<svg role="img" aria-label="'+html.escape(alt)+'" ',svg,count=1)
        parts.append('<figure>'+svg+'<figcaption>'+rich(FIGURES[t][1],True)+'</figcaption></figure>')
    elif kind=='table':
        d=TABLES[t];parts.append('<table><caption>'+rich(d['caption'],True)+'</caption><thead><tr>'+''.join('<th scope="col">'+rich(v,True)+'</th>' for v in d['headers'])+'</tr></thead><tbody>')
        for row in d['rows']:parts.append('<tr>'+''.join('<td>'+rich(v,True)+'</td>' for v in row)+'</tr>')
        parts.append('</tbody></table>')
parts.append('<section class="references"><h2>References</h2>')
for k in KEYS:parts.append(f'<p id="ref-{NUM[k]}">'+html.escape(reftext(k))+f' <a href="{html.escape(REG[k]["source_url"])}">{html.escape(REG[k].get("link_label") or REG[k]["doi"])}</a></p>')
parts.append('</section></article></body></html>');HTML.write_text('\n'.join(parts),encoding='utf-8')

def bibescape(t):return clean(t).replace('&','\\&').replace('%','\\%').replace('_','\\_').replace('{','\\{').replace('}','\\}')
bibs=[]
for k in KEYS:
    r=REG[k];typ=r.get('bib_type') or ('inproceedings' if k=='IsoFormer2024' else 'article')
    names=[]
    for a in r.get('author_list',[]):
        if a.get('lastName'):names.append(a['lastName']+', '+a.get('firstName',a.get('initials','')))
        elif a.get('collectiveName'):names.append('{'+a['collectiveName']+'}')
        elif a.get('fullName'):names.append('{'+a['fullName']+'}')
    fields={'title':'{'+clean(r['title']).rstrip('.')+'}','author':' and '.join(names) or '{'+r.get('authors','')+'}','year':r['year'],'booktitle' if typ=='inproceedings' else 'journal':r.get('journal',''),'volume':r.get('volume'),'pages':r.get('pages'),'doi':r['doi'],'url':r['source_url'],'note':r.get('version_note')}
    if typ in ('phdthesis','misc'):
        fields.pop('journal')
        if typ=='phdthesis':
            fields['school']=r['school']
        else:
            fields['howpublished']=r['journal']
    # Author-group braces and protected title braces are intentional BibTeX syntax.
    lines=[]
    for f,v in fields.items():
        if v:
            value=clean(v).replace('&','\\&').replace('%','\\%')
            lines.append('  '+f+' = {'+value+'}')
    bibs.append('@'+typ+'{'+k+',\n'+',\n'.join(lines)+'\n}')
(P/'references.bib').write_text('\n\n'.join(bibs)+'\n',encoding='utf-8')
(QA/'citation_order.json').write_text(json.dumps(KEYS,indent=2),encoding='utf-8')
from typeset import build_pdf
build_pdf(P, OUT, TITLE, BYLINE, DATE, ABSTRACT, KEYWORDS, BLOCKS, TABLES, FIGURES, KEYS, REG, reftext)
reader=PdfReader(OUT);texts=[pg.extract_text() or '' for pg in reader.pages]
(QA/'pdf_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{t}' for i,t in enumerate(texts)),encoding='utf-8')
bodywords=len(' '.join(t for k,t in BLOCKS if k=='p').split())+len(ABSTRACT.split())
summary={'pdf':str(OUT),'html':str(HTML),'pages':len(texts),'prose_words_including_abstract':bodywords,'references':len(KEYS),'tables':len(TABLES),'figures':len(FIGURES),'page_word_counts':[len(t.split()) for t in texts],'pdf_bytes':OUT.stat().st_size,'link_annotations':sum(len(pg['/Annots']) if '/Annots' in pg else 0 for pg in reader.pages)}
(QA/'pdf_checks.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))
