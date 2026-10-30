"""T15 offline shadow: Haiku 5.5 vs Haiku 4.5 on the news-sentiment prompt. Tooling, not a strategy trial.

Nothing live imports this. It reads no journal, places no order and changes no config. It calls the
same SYSTEM_PROMPT / max_tokens / number parsing as llm_sentiment.score_headline, once per model per
headline, so the cost and the scores are what the backend would see.

Pass rule (written before any run): sign agreement >= 95% and mean absolute score difference <= 0.1.
Sign: score > +0.05 is +, < -0.05 is -, else 0. Switching the live model would change a strategy
input, so it is NOT a tooling change: it needs a pre-registered, counted trial (handover memory).

From backend/, with backend/.venv:
    .venv/bin/python -m research.haiku55_shadow collect            # 200 headlines, free Google News RSS
    ANTHROPIC_API_KEY=... .venv/bin/python -m research.haiku55_shadow score    # ~400 calls, a few cents
    .venv/bin/python -m research.haiku55_shadow report             # table into docs/research/tooling/
The key is read from the environment only and is never printed or written.
"""
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "research" / "tooling"
HEADLINES, SCORES, REPORT = OUT / "haiku55-headlines.json", OUT / "haiku55-scores.json", OUT / "haiku55-shadow.md"
MODELS = {"old": os.environ.get("OLD_MODEL", "claude-haiku-4-5-20251001"),
          "new": os.environ.get("NEW_MODEL", "claude-haiku-5-5")}  # new id unverified: list models before the first run
PRICE = {"old": (1.0, 5.0), "new": (0.10, 0.50)}  # USD per M tokens in/out (tools.md T15 evidence)
N, BAND = 200, 0.05


def collect():
    sys.path.insert(0, str(ROOT / "backend"))
    import news_sentiment as ns
    rows = list(csv.DictReader(open(ROOT / "backend" / "data" / "nifty100.csv")))
    out, seen = [], set()
    for r in rows:
        sym, name = r["Symbol"], r["Company Name"]
        try:
            items = ns._google_news(ns.search_query(sym, name))
        except Exception as exc:
            print(f"{sym}: {exc}", file=sys.stderr)
            continue
        pats = ns.name_patterns(sym, name)
        for it in items:
            key = re.sub(r"\W+", "", it["title"].lower())[:80]
            if key and key not in seen and any(p.search(it["title"]) for p in pats):
                seen.add(key)
                out.append({"symbol": sym, "title": it["title"], "publisher": it.get("publisher")})
        print(f"{sym}: total {len(out)}", file=sys.stderr)
        if len(out) >= N:
            break
        time.sleep(0.5)
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(out[:N], open(HEADLINES, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {min(len(out), N)} headlines to {HEADLINES}")


def score():
    import anthropic
    sys.path.insert(0, str(ROOT / "backend"))
    from llm_sentiment import SYSTEM_PROMPT
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    heads = json.load(open(HEADLINES))
    res = []
    for h in heads:
        row = {"title": h["title"]}
        for tag, model in MODELS.items():
            r = client.messages.create(model=model, max_tokens=30, system=SYSTEM_PROMPT, messages=[
                {"role": "user", "content": f"Headline: {h['title']}\nSummary: (none)"}])
            m = re.search(r"-?\d*\.?\d+", r.content[0].text.strip())
            row[tag] = max(-1.0, min(1.0, float(m.group()))) if m else None
            row[tag + "_tok"] = [r.usage.input_tokens, r.usage.output_tokens]
        res.append(row)
    json.dump({"models": MODELS, "rows": res}, open(SCORES, "w"), indent=1, ensure_ascii=False)
    print(f"scored {len(res)} headlines")


def sign(x):
    return 1 if x > BAND else -1 if x < -BAND else 0


def report():
    d = json.load(open(SCORES))
    ok = [r for r in d["rows"] if r["old"] is not None and r["new"] is not None]
    agree = sum(sign(r["old"]) == sign(r["new"]) for r in ok) / len(ok)
    mad = sum(abs(r["old"] - r["new"]) for r in ok) / len(ok)
    cost = {t: sum(r[t + "_tok"][0] * PRICE[t][0] + r[t + "_tok"][1] * PRICE[t][1] for r in ok) / 1e6 for t in PRICE}
    bad = sorted(ok, key=lambda r: -abs(r["old"] - r["new"]))[:10]
    md = [f"# Haiku 5.5 vs 4.5 shadow ({len(ok)} of {len(d['rows'])} headlines scored)", "",
          f"Models: old `{d['models']['old']}`, new `{d['models']['new']}`.", "",
          "| measure | value | pass rule | result |", "|---|---|---|---|",
          f"| sign agreement | {agree:.1%} | >= 95% | {'PASS' if agree >= .95 else 'FAIL'} |",
          f"| mean abs score difference | {mad:.3f} | <= 0.1 | {'PASS' if mad <= .1 else 'FAIL'} |",
          f"| cost for these {len(ok)} headlines | old ${cost['old']:.4f}, new ${cost['new']:.4f} | n/a | n/a |", "",
          "Ten largest disagreements:", "", "| old | new | headline |", "|---|---|---|"]
    md += [f"| {r['old']:+.2f} | {r['new']:+.2f} | {r['title'][:110].replace('|', '/')} |" for r in bad]
    REPORT.write_text("\n".join(md) + "\n")
    print("\n".join(md[:8]))


if __name__ == "__main__":
    {"collect": collect, "score": score, "report": report}[sys.argv[1]]()
