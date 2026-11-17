"""Build the whitepaper from one source: whitepaper/paper.md.

Writes whitepaper/index.html (styled page, served by GitHub Pages) and replaces the
paper at the top of README.md (everything above "# Code and reproduction").

Source format: Markdown subset plus
  ::: kicker | dek | meta | refs  ... :::     styled blocks
  ::: ledger ... :::                         key numbers, one per line: value | label [| loss]
  ![alt](fig/x.png) followed by ": caption"  a figure with caption
  > text                                     the callout box
Run: python whitepaper/build.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATUS = {"Supported": "s-strong", "Model only": "s-mixed", "Range": "s-mixed", "Mixed": "s-mixed",
          "Not shown": "s-open", "Not found": "s-open"}


def inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def parse(src: str):
    """Yield (kind, payload) blocks."""
    lines = src.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith(":::"):
            name = line[3:].strip()
            body = []
            i += 1
            while not lines[i].startswith(":::"):
                body.append(lines[i])
                i += 1
            i += 1
            yield ("block", (name, body))
            continue
        m = re.match(r"(#{1,3}) (.*)", line)
        if m:
            yield (f"h{len(m.group(1))}", m.group(2))
            i += 1
            continue
        if line.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            cap = ""
            if i + 1 < len(lines) and lines[i + 1].startswith(": "):
                cap = lines[i + 1][2:]
                i += 1
            yield ("figure", (m.group(1), m.group(2), cap))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+:?|:?-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            yield ("table", rows)
            continue
        if line.startswith("> "):
            body = []
            while i < len(lines) and lines[i].startswith(">"):
                body.append(lines[i][1:].strip())
                i += 1
            yield ("callout", " ".join(body))
            continue
        if re.match(r"(- |\d+\. )", line):
            ordered = bool(re.match(r"\d+\. ", line))
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i]):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                i += 1
            yield ("list", (ordered, items))
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#|:::|!\[|\||> |- |\d+\. )", lines[i]):
            para.append(lines[i])
            i += 1
        yield ("p", " ".join(para))


def to_html(blocks) -> str:
    out = []
    in_header = True
    for kind, x in blocks:
        if kind == "block":
            name, body = x
            if name == "ledger":
                cells = []
                for b in body:
                    parts = [p.strip() for p in b.split("|")]
                    cls = "v loss" if len(parts) > 2 and parts[2] == "loss" else "v"
                    cells.append(f'  <div role="listitem"><span class="{cls}">{inline(parts[0])}</span>'
                                 f'<span class="l">{inline(parts[1])}</span></div>')
                out.append('<div class="ledger" role="list">\n' + "\n".join(cells) + "\n</div>")
            else:
                cls = {"kicker": "kicker", "dek": "dek", "meta": "meta", "refs": "refs"}[name]
                out.append(f'<p class="{cls}">{inline(" ".join(body))}</p>')
                if name == "meta" and in_header:
                    out.append("</header>")
                    in_header = False
        elif kind == "h1":
            out.insert(0, '<header class="paper-head">')
            out.append(f"<h1>{inline(x)}</h1>")
        elif kind == "h2":
            m = re.match(r"(\d+)\. (.*)", x)
            num, title = (m.group(1), m.group(2)) if m else ("·", x)
            out.append(f'<h2><span class="num">{num}</span>{inline(title)}</h2>')
        elif kind == "h3":
            out.append(f"<h3>{inline(x)}</h3>")
        elif kind == "p":
            out.append(f"<p>{inline(x)}</p>")
        elif kind == "list":
            ordered, items = x
            tag = "ol" if ordered else "ul"
            out.append(f'<{tag} class="tight">\n' + "\n".join(f"  <li>{inline(it)}</li>" for it in items) + f"\n</{tag}>")
        elif kind == "figure":
            alt, src, cap = x
            m = re.match(r"\*\*(.+?)\*\*\s*(.*)", cap)
            capx = f"<b>{inline(m.group(1))}</b> {inline(m.group(2))}" if m else inline(cap)
            out.append(f'<figure>\n  <div class="plate"><img src="{src}" alt="{html.escape(alt)}"></div>\n'
                       f"  <figcaption>{capx}</figcaption>\n</figure>")
        elif kind == "table":
            head, *rows = x
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            body = []
            for r in rows:
                tds = []
                for j, c in enumerate(r):
                    if head[j] == "Status":
                        tds.append(f'<td><span class="status {STATUS.get(c, "s-mixed")}">{inline(c)}</span></td>')
                    else:
                        tds.append(f"<td>{inline(c)}</td>")
                body.append("<tr>" + "".join(tds) + "</tr>")
            out.append('<div class="table-wrap">\n<table>\n  <thead><tr>' + th + "</tr></thead>\n  <tbody>\n    "
                       + "\n    ".join(body) + "\n  </tbody>\n</table>\n</div>")
        elif kind == "callout":
            out.append(f'<div class="callout">\n  <p>{inline(x)}</p>\n</div>')
    return "\n".join(out)


def to_markdown(blocks) -> str:
    out = []
    for kind, x in blocks:
        if kind == "block":
            name, body = x
            text = " ".join(body)
            if name == "ledger":
                out.append("| | |\n|---|---|\n" + "\n".join(
                    f"| **{b.split('|')[0].strip()}** | {b.split('|')[1].strip()} |" for b in body))
            elif name == "kicker":
                out.append(f"*{text}*")
            elif name == "dek":
                out.append(f"*{text}* **[Read the formatted whitepaper](https://wesboyt.github.io/elastic-matching/whitepaper/)**.")
            elif name == "refs":
                out.append(f"**References.** {text}")
            else:
                out.append(text)
        elif kind in ("h1", "h2", "h3"):
            out.append("#" * int(kind[1]) + " " + x)
        elif kind == "p":
            out.append(x)
        elif kind == "list":
            ordered, items = x
            out.append("\n".join((f"{k + 1}. " if ordered else "- ") + it for k, it in enumerate(items)))
        elif kind == "figure":
            alt, src, cap = x
            out.append(f"![{alt}](whitepaper/{src})\n\n*{cap.replace('**', '')}*")
        elif kind == "table":
            head, *rows = x
            lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
            for r in rows:
                lines.append("| " + " | ".join(f"**{c}**" if head[j] == "Status" else c for j, c in enumerate(r)) + " |")
            out.append("\n".join(lines))
        elif kind == "callout":
            out.append("> " + x)
    return "\n\n".join(out) + "\n"


def main():
    src = (HERE / "paper.md").read_text(encoding="utf-8")
    blocks = list(parse(src))
    page = (HERE / "template.html").read_text(encoding="utf-8").replace("{{CONTENT}}", to_html(blocks))
    (HERE / "index.html").write_text(page, encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    code = readme[readme.index("# Code and reproduction"):]
    (ROOT / "README.md").write_text(to_markdown(blocks) + "\n---\n\n" + code, encoding="utf-8")
    missing = [s for _, (a, s, c) in [(k, v) for k, v in blocks if k == "figure"] if not (HERE / s).exists()]
    print("built whitepaper/index.html and README.md" + (f"; MISSING figures: {missing}" if missing else ""))


if __name__ == "__main__":
    main()
