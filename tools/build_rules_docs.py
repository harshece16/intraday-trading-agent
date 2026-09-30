#!/usr/bin/env python3
"""Build the rules checklist from its one source, docs/architecture/rules.json.

    python3 tools/build_rules_docs.py            # write RULES.md and rules.html
    python3 tools/build_rules_docs.py --check    # exit 1 if either file is stale
    python3 tools/build_rules_docs.py --artifact OUT.html   # also write the hosted-page variant

RULES.md is the GitHub view: one collapsible block per rule. rules.html is the
same catalogue as an interactive page (search, filters, ticks) that opens
straight from disk. Its diagrams and the trading-day table are read from
HLD.md, so the page never drifts from the design document.

Python 3.9 compatible; standard library only.
"""
import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "docs", "architecture")
RULES_JSON = os.path.join(ARCH, "rules.json")
HLD_MD = os.path.join(ARCH, "HLD.md")
RULES_MD = os.path.join(ARCH, "RULES.md")
RULES_HTML = os.path.join(ARCH, "rules.html")
TEMPLATE = os.path.join(ROOT, "tools", "rules_page.template.html")
REPO = "https://github.com/harshece16/intraday-trading-agent"
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
# The standalone page draws its own diagrams, in the page's palette, in both themes.
MERMAID_THEME = """(function () {
  if (!window.mermaid) return;
  var cs = getComputedStyle(document.documentElement);
  function v(n) { return cs.getPropertyValue(n).trim(); }
  mermaid.initialize({
    startOnLoad: true, theme: "base",
    themeVariables: {
      primaryColor: v("--sunken"), primaryTextColor: v("--ink"), primaryBorderColor: v("--ink-3"),
      lineColor: v("--ink-3"), textColor: v("--ink"), secondaryColor: v("--surface"), tertiaryColor: v("--paper"),
      clusterBkg: v("--paper"), clusterBorder: v("--rule"), edgeLabelBackground: v("--surface"),
      titleColor: v("--ink-2"), fontFamily: '"Instrument Sans", system-ui, sans-serif', fontSize: "13px",
      background: v("--surface"), mainBkg: v("--sunken"), nodeBorder: v("--ink-3"),
      stateBkg: v("--sunken"), stateLabelColor: v("--ink"), compositeBackground: v("--paper"),
      compositeTitleBackground: v("--sunken"), compositeBorder: v("--rule"), altBackground: v("--paper"),
      transitionColor: v("--ink-3"), transitionLabelColor: v("--ink"), labelBackgroundColor: v("--surface"),
      specialStateColor: v("--ink-3"), innerEndBackground: v("--surface"), labelColor: v("--ink")
    }
  });
})();
"""
STATUS_WORD = {"active": "Active", "paper-only": "Paper only", "off-by-default": "Off by default",
               "pending": "Pending", "retired": "Retired"}


def load():
    with open(RULES_JSON, encoding="utf-8") as fh:
        return json.load(fh)


# --- reading HLD.md --------------------------------------------------------------------

def hld_figures(text):
    """Every mermaid block with the heading above it and the paragraph below it."""
    figs, heading, lines = [], None, text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^#{2,3}\s+(.*)$", line)
        if m:
            heading = re.sub(r"^\d+(\.\d+)*\.?\s+", "", m.group(1)).strip()
        if line.strip() == "```mermaid":
            j = i + 1
            while j < len(lines) and lines[j].strip() != "```":
                j += 1
            src = "\n".join(lines[i + 1:j])
            k, cap = j + 1, []
            while k < len(lines) and not lines[k].strip():
                k += 1
            while k < len(lines) and lines[k].strip() and not re.match(r"^(\||#|```|- |\d+\. )", lines[k]):
                cap.append(lines[k].strip())
                k += 1
            figs.append({"title": heading or "Diagram", "source": src, "caption": " ".join(cap)})
            i = j
        i += 1
    return figs


def hld_day_table(text):
    """The markdown table under the 'A trading day' heading, as rows of cells."""
    m = re.search(r"^###\s+[\d.]*\s*A trading day\s*$", text, re.M)
    if not m:
        return []
    rows = []
    for line in text[m.end():].splitlines():
        if line.startswith("#"):
            break
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.match(r"^:?-+:?$", c) for c in cells):
                continue
            rows.append(cells)
        elif rows:
            break
    return rows


def inline_html(s):
    out = html.escape(s, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)


# --- the interactive page ----------------------------------------------------------------

def build_page(cat, standalone):
    with open(TEMPLATE, encoding="utf-8") as fh:
        page = fh.read()
    with open(HLD_MD, encoding="utf-8") as fh:
        hld = fh.read()
    figs = []
    for f in hld_figures(hld):
        cap = "<p>%s</p>" % inline_html(f["caption"]) if f["caption"] else ""
        figs.append('<section class="fig"><h2>%s</h2>%s<div class="fig-scroll"><pre class="mermaid">%s</pre></div></section>'
                    % (html.escape(f["title"], quote=False), cap, html.escape(f["source"], quote=False)))
    rows = hld_day_table(hld)
    table = ""
    if rows:
        head = "".join("<th>%s</th>" % inline_html(c) for c in rows[0])
        body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline_html(c) for c in r) for r in rows[1:])
        table = "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (head, body)
    data = json.dumps({k: cat[k] for k in ("as_of", "statuses", "areas", "rules")}, ensure_ascii=False,
                      separators=(",", ":")).replace("</", "<\\/")
    page = page.replace("{{FIGURES}}", "\n      ".join(figs)).replace("{{DAY_TABLE}}", table).replace("{{RULES_JSON}}", data)
    if not standalone:
        return page
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
            + page + '\n<script src="%s"></script>\n<script>\n%s</script>\n</body>\n</html>\n' % (MERMAID_CDN, MERMAID_THEME))


# --- RULES.md ------------------------------------------------------------------------------

def md(s):
    """Prose for a GitHub table cell or paragraph."""
    s = (s or "").replace("\\", "\\\\")
    for ch in ("*", "$", "|", "`"):
        s = s.replace(ch, "\\" + ch)
    return s.replace("<", "&lt;").replace("\n", " ")


def code(s):
    s = (s or "").replace("|", "\\|").replace("\n", " ")
    fence = "``" if "`" in s else "`"
    pad = " " if fence == "``" else ""
    return fence + pad + s + pad + fence


def first_sentence(s, limit=150):
    m = re.search(r"^(.+?[.!?])(\s|$)", s)
    out = m.group(1) if m else s
    if len(out) > limit:
        out = out[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out


def build_md(cat):
    rules, areas = cat["rules"], cat["areas"]
    out = []
    w = out.append
    w("# Trader Sahab — Rules checklist")
    w("")
    w("<!-- Generated by tools/build_rules_docs.py from docs/architecture/rules.json. Do not edit by hand. -->")
    w("")
    w("Every rule the system follows: what it says, why it exists, the code that enforces it, and how to see it "
      "being followed. **%d rules** in %d areas, as of %s." % (len(rules), len([a for a in areas if any(r["area"] == a["id"] for r in rules)]), cat["as_of"]))
    w("")
    w("Companions: [High-Level Design](HLD.md) · [Low-Level Design](LLD.md) · [Knowledge graph](KNOWLEDGE_GRAPH.md)")
    w("")
    w("## How to use this page")
    w("")
    w("- **Read a rule:** click it to open the reason, the enforcing code, the current setting and the check.")
    if cat.get("interactive_url"):
        w("- **Tick rules off:** the [interactive rulebook](%s) has search, filters and ticks that are saved. "
          "The same page is in the repository as [`rules.html`](rules.html); download it and open it in a browser." % cat["interactive_url"])
    else:
        w("- **Tick rules off:** open [`rules.html`](rules.html) in a browser. It has search, filters and ticks.")
    w("- **Run a checklist on GitHub:** open a new issue and pick *Pre-market checklist*, *New strategy checklist* "
      "or *Go-live readiness*. Those checkboxes can be ticked in the issue.")
    w("- **Change a rule:** edit [`rules.json`](rules.json), run `python3 tools/build_rules_docs.py`, and commit all three files. "
      "A test fails if this page is stale or a rule points at code that no longer exists.")
    w("")
    w("## Status")
    w("")
    w("| Status | Meaning | Rules |")
    w("| --- | --- | --- |")
    for k, meaning in cat["statuses"].items():
        n = sum(1 for r in rules if r["status"] == k)
        if n:
            w("| **%s** | %s | %d |" % (STATUS_WORD[k], md(meaning), n))
    w("")
    w("## Areas")
    w("")
    w("| Area | Rules | Enforced now | With a test | Known gaps |")
    w("| --- | --- | --- | --- | --- |")
    for a in areas:
        rs = [r for r in rules if r["area"] == a["id"]]
        if not rs:
            continue
        gaps = sorted({n for r in rs for n in r.get("issues", [])})
        w("| [%s](#%s) | %d | %d | %d | %s |" % (
            a["title"], anchor(a["title"]), len(rs),
            sum(1 for r in rs if r["status"] in ("active", "paper-only")),
            sum(1 for r in rs if r.get("test")),
            " ".join("[#%d](%s/issues/%d)" % (n, REPO, n) for n in gaps) or "–"))
    w("")
    for a in areas:
        rs = [r for r in rules if r["area"] == a["id"]]
        if not rs:
            continue
        w("## %s" % a["title"])
        w("")
        w(md(a["blurb"]))
        w("")
        for r in rs:
            gaps = "".join(" · known gap #%d" % n for n in r.get("issues", []))
            w("<details>")
            w("<summary><code>%s</code> <b>%s</b>%s — %s</summary>" % (
                r["id"], STATUS_WORD[r["status"]], html.escape(gaps, quote=False),
                html.escape(first_sentence(r["rule"]), quote=False)))
            w("")
            if first_sentence(r["rule"]) != r["rule"].strip():
                w(md(r["rule"]))            # the summary was shortened; give the whole rule
                w("")
            w("| | |")
            w("| --- | --- |")
            if r.get("why"):
                w("| **Why** | %s |" % md(r["why"]))
            if r.get("enforced_in"):
                w("| **Enforced in** | %s |" % code(r["enforced_in"]))
            if r.get("config"):
                w("| **Setting** | %s |" % code(r["config"]))
            if r.get("verify"):
                w("| **How to check** | %s |" % md(r["verify"]))
            if r.get("test"):
                w("| **Test** | %s |" % code(r["test"]))
            if r.get("source"):
                w("| **Source** | %s |" % md(r["source"]))
            for n in r.get("issues", []):
                w("| **Known gap** | [#%d](%s/issues/%d) |" % (n, REPO, n))
            w("")
            w("</details>")
            w("")
    return "\n".join(out).rstrip("\n") + "\n"


def anchor(title):
    s = re.sub(r"[^\w\- ]", "", title.strip().lower())
    return s.replace(" ", "-")


# --- entry point -----------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if RULES.md or rules.html is stale")
    ap.add_argument("--artifact", metavar="PATH", help="also write the hosted-page variant (no html/head/body wrapper)")
    args = ap.parse_args(argv)
    cat = load()
    wanted = {RULES_MD: build_md(cat), RULES_HTML: build_page(cat, standalone=True)}
    if args.check:
        stale = []
        for path, text in wanted.items():
            try:
                with open(path, encoding="utf-8") as fh:
                    if fh.read() != text:
                        stale.append(path)
            except OSError:
                stale.append(path)
        if stale:
            print("Stale: %s. Run python3 tools/build_rules_docs.py" % ", ".join(os.path.relpath(p, ROOT) for p in stale))
            return 1
        print("Rules documents are up to date (%d rules)." % len(cat["rules"]))
        return 0
    for path, text in wanted.items():
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s" % os.path.relpath(path, ROOT))
    if args.artifact:
        with open(args.artifact, "w", encoding="utf-8") as fh:
            fh.write(build_page(cat, standalone=False))
        print("wrote %s" % args.artifact)
    return 0


if __name__ == "__main__":
    sys.exit(main())
