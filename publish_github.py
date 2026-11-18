"""Build a distributable review snapshot and optionally publish it to GitHub."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
DEFAULT_REPO = "Kohze/developmental-transcript-switches"
STEM = "Developmental_transcript_switches"
INPUTS = [
    "manuscript.md", "publish_github.py", "build_review.py", "typeset.py",
    "preamble.tex", "requirements.txt", "switch_figures.py", "figure_comparisons.py",
    "figure_descriptions.json", "figure_legends.json", "qa/validate.py", "qa/check_figures.py",
    "qa/display_item_credits.csv", "figures/data/snap25.csv", "research/source_registry.json",
    "research/figure_provenance.csv", "research/41467_2018_4559_MOESM10_ESM.xlsx",
    "research/41467_2018_4559_MOESM7_ESM.xlsx", "research/elife-46042-fig4-data1-v1.xlsx",
    "research/elife-46042-fig7-data1-v1.xlsx", "research/elife-59224-fig1-data1-v2.xlsx",
]
FIGURES = ("cortical", "robo", "routes", "snap25", "fruitless", "timing")
OUTPUTS = ["references.bib", "REPRODUCE.md", *(f"{STEM}.{ext}" for ext in ("pdf", "tex", "html")),
           *(f"figures/{fig}.{ext}" for fig in FIGURES for ext in ("pdf", "svg"))]


def run(args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, text=True)


def build(stage, repo, tag):
    for name in INPUTS:
        dest = stage / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    url = f"https://github.com/{repo}/tree/{tag}"
    manuscript = stage / "manuscript.md"
    before, sep, rest = manuscript.read_text(encoding="utf-8").partition("## Data and Code Availability\n\n")
    section, end, after = rest.partition("\n\n## ")
    citation = f"The editable manuscript, figure inputs and plotting code are archived at [{repo}, {tag}]({url})."
    section, count = re.subn(r"(?m)^(?:The planned GitHub archive is|The editable manuscript, figure inputs and plotting code are archived at) \[[^\n]+\]\(https://github\.com/[^\n)]+\)\.$", lambda _: citation, section)
    if not sep or not end or count != 1:
        raise ValueError("Expected one GitHub citation in Data and Code Availability.")
    manuscript.write_text(before + sep + section + end + after, encoding="utf-8")
    (stage / "REPRODUCE.md").write_text(
        "# Transcript switches and the timing of development\n\n"
        f"Version [{tag}]({url}). Open {STEM}.pdf or {STEM}.html to read the review.\n\n"
        "Install Python, the packages in requirements.txt and Tectonic. "
        "Set TECTONIC to its executable path if necessary. From this directory run:\n\n"
        "\x60\x60\x60sh\npython -m pip install -r requirements.txt\npython build_review.py\n"
        "python qa/validate.py\npython qa/check_figures.py\n\x60\x60\x60\n\n"
        "Source studies, workbooks and figure credits are listed in research/figure_provenance.csv "
        "and qa/display_item_credits.csv.\n", encoding="utf-8")
    for script in ("build_review.py", "qa/validate.py", "qa/check_figures.py"):
        run([sys.executable, script], stage)
    return url


def publish(stage, checkout, repo, tag, create_public):
    remote = f"https://github.com/{repo}.git"
    if create_public:
        run(["gh", "repo", "create", repo, "--public"], ROOT)
    run(["git", "clone", "--", remote, str(checkout)], ROOT)
    if subprocess.run(["git", "rev-parse", "--verify", "--quiet", "refs/tags/" + tag],
                      cwd=checkout, stdout=subprocess.DEVNULL).returncode == 0:
        raise ValueError(f"Tag {tag} already exists. Choose a new tag for a changed release.")
    managed = checkout / "REPRODUCE.md"
    prior_release = managed.is_file() and managed.read_text(encoding="utf-8").startswith(
        "# Transcript switches and the timing of development\n")
    for name in INPUTS + OUTPUTS:
        dest = checkout / name
        if dest.is_symlink() or not dest.resolve().is_relative_to(checkout.resolve()):
            raise ValueError(f"Unexpected repository path: {name}")
        if dest.exists() and not prior_release:
            raise ValueError(f"The target already contains {name}. Use a dedicated review repository.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(stage / name, dest)
    run(["git", "add", "--", *INPUTS, *OUTPUTS], checkout)
    run(["git", "commit", "-m", f"Publish developmental transcript switches review {tag}"], checkout)
    run(["git", "tag", tag], checkout)
    branch = subprocess.check_output(["git", "symbolic-ref", "HEAD"], cwd=checkout, text=True).strip()
    run(["git", "push", "--atomic", "origin", f"HEAD:{branch}", f"refs/tags/{tag}"], checkout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub OWNER/REPOSITORY")
    parser.add_argument("--tag", default="v1.0.0", help="Version tag, e.g. v1.0.1")
    parser.add_argument("--push", action="store_true", help="Push to the named repository")
    parser.add_argument("--create-public", action="store_true", help="Create the named public repository first (requires gh)")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", args.repo):
        parser.error("--repo must be a GitHub owner/repository")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", args.tag):
        parser.error("--tag must use the form v1.0.0")
    if args.create_public and not args.push:
        parser.error("--create-public requires --push")
    # A sibling staging directory preserves the review builder's local Tectonic discovery.
    with tempfile.TemporaryDirectory(prefix="review-build-", dir=ROOT.parent) as work:
        stage = Path(work)
        url = build(stage, args.repo, args.tag)
        if args.push:
            publish(stage, stage / "checkout", args.repo, args.tag, args.create_public)
        kind = "release" if args.push else "preview"
        archive = ROOT / f"{STEM}_{args.tag}_{kind}.zip"
        draft_zip = stage / "snapshot.zip"
        with ZipFile(draft_zip, "w", ZIP_DEFLATED) as zipped:
            for name in INPUTS + OUTPUTS:
                zipped.write(stage / name, name)
        draft_zip.replace(archive)
    if args.push:
        print(f"Published {url}")
    else:
        print(f"Local preview for {url}. No GitHub changes made.")
    print(archive)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
