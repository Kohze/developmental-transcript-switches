"""Render the reading copy using the November nORFs LaTeX manuscript layout."""
import os
from pathlib import Path
import re
import shutil
import subprocess


def tex(text):
    link = re.search(r"\[([^]\n]+)\]\((https://[^\s)]+)\)", str(text))
    if link:
        return tex(text[:link.start()]) + r"\href{" + link[2] + "}{" + tex(link[1]) + "}" + tex(text[link.end():])
    escapes = {"–": "--", "—": "---", "’": "'", "β": r"\(\beta\)", "Ž": r"\v{Z}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$",
               "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "−": r"\ensuremath{-}"}
    text = "".join(escapes.get(c, c) for c in str(text))
    text = text.replace("BBSRC", r"\mbox{BBSRC}")
    text = text.replace("Ferguson-Smith", r"\mbox{Ferguson-Smith}")
    text = re.sub(r"\b(Figure|Table) (?=\d)", r"\1~", text)
    text = re.sub(r"\*([^*\n]+)\*", lambda m: r"\textit{" + m[1] + "}", text)
    return re.sub(r"\[(@[^\]]+)\]", lambda m: r"\cite{" + ",".join(re.findall(r"@(\w+)", m[1])) + "}", text)


def build_pdf(root, out, title, byline, date, abstract, keywords, blocks, tables, figures, keys, records, reference):
    name_line, *affiliations = byline.splitlines()
    def affiliation_markers(line):
        return re.sub(r"<sup>([0-9,]+)</sup>", lambda m: r"\textsuperscript{" + m[1] + "}", tex(line.strip()))
    names = affiliation_markers(name_line)
    author_block = names
    if affiliations:
        author_block += r"\\[4pt]" + r"\\".join(r"\small " + affiliation_markers(line) for line in affiliations)
    author_metadata = re.sub(r"<sup>[0-9,]+</sup>", "", name_line).strip()
    lines = [(root / "preamble.tex").read_text(encoding="utf8"),
             r"\hypersetup{hidelinks,pdftitle={" + tex(title) + "},pdfauthor={" + tex(author_metadata) + "},pdfkeywords={" + tex(keywords) + "}}",
             r"\title{" + tex(title) + "}", r"\author{" + author_block + "}",
             r"\date{" + tex(date) + "}", r"\begin{document}", r"\maketitle",
             r"\begin{abstract}", tex(abstract), r"\end{abstract}",
             r"\noindent\textbf{Keywords:} " + tex(keywords), r"\clearpage"]
    declarations = False
    for kind, text in blocks:
        if kind == "h1":
            if text == "Generative AI disclosure":
                declarations = True
            lines.append((r"\section*{" if declarations else r"\section{") + tex(text) + "}")
        elif kind == "h2":
            lines.append(r"\subsection{" + tex(text) + "}")
        elif kind == "p":
            lines.append(tex(text))
        elif kind == "figure":
            caption = re.sub(r"^Figure \d+\.\s*", "", figures[text][1])
            lines.extend([r"\begin{figure}[htbp]",r"\centering",
                          r"\includegraphics[width=\linewidth,height=.61\textheight,keepaspectratio]{figures/" + text + ".pdf}",
                          r"\caption{" + tex(caption) + "}",r"\end{figure}"])
        elif kind == "table":
            d = tables[text]
            caption = re.sub(r"^Table \d+\.\s*", "", d["caption"])
            lines.extend([r"\begin{table}[htbp]",r"\caption{" + tex(caption) + "}",r"\small",
                          r"\begin{tabularx}{\textwidth}{@{}*{3}{>{\raggedright\arraybackslash}X}@{}}\toprule",
                          " & ".join(r"\textbf{"+tex(v)+"}" for v in d["headers"]) + r"\\\midrule"])
            for index, row in enumerate(d["rows"]):
                lines.append(" & ".join(map(tex, row)) + r"\\")
                if index < len(d["rows"]) - 1:
                    lines.append(r"\addlinespace[9pt]")
            lines.extend([r"\bottomrule\end{tabularx}",r"\end{table}"])
    lines.extend([r"\begin{thebibliography}{99}",r"\small",r"\setlength{\itemsep}{1.5pt}"])
    for key in keys:
        body = re.sub(r"^\[\d+\] ", "", reference(key))
        record = records[key]
        label = tex(record["link_label"]) if record.get("link_label") else r"\nolinkurl{" + record["doi"] + "}"
        lines.append(r"\bibitem{" + key + "}" + tex(body) + r" \href{" + record["source_url"] + "}{" + label + "}.")
    lines.extend([r"\end{thebibliography}", r"\end{document}"])
    manuscript = out.with_suffix(".tex")
    manuscript.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    local_tools = root.parents[1] / "norfs/tmp/ssrn_tools"
    engine = os.getenv("TECTONIC") or shutil.which("tectonic") or str(local_tools / "tectonic/tectonic.exe")
    env = os.environ.copy()
    if (local_tools / "tectonic_cache").is_dir():
        env.setdefault("TECTONIC_CACHE_DIR", str(local_tools / "tectonic_cache"))
    command = [engine]
    # The local offline bundle lacks the italic Latin Modern metrics.
    # A full Tectonic bundle already provides these files.
    miktex_fonts = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/MiKTeX/fonts"
    for subfolder in ("tfm/public/lm", "type1/public/lm"):
        font_dir = miktex_fonts / subfolder
        if font_dir.is_dir():
            command.extend(["-Z", "search-path=" + str(font_dir)])
    if env.get("TECTONIC_CACHE_DIR"):
        command.append("--only-cached")
    result = subprocess.run(command + [manuscript.name], cwd=root, env=env, capture_output=True)
    (root / "qa/compile.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr).decode(errors="replace"))

