"""L46's family gate (prereg-tsfm-family.md §4): L40's §8 checks per model and horizon,
with Benjamini-Hochberg at q = 0.10 across all 18 tests. A void model enters at p = 1.

    python -m research.l46_family_gate --data-dir docs/research/data
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from research import kronos_feature_ic as k  # noqa: E402
from research.tsfm_family_ic import MODELS, N_TESTS_IN_FAMILY  # noqa: E402

VOID_SUMMARY = {"sessions": 0,
                "spread": {"mean": None, "t": None, "p": None, "halves": [{"mean": None}, {"mean": None}]},
                "pic": {"mean": None, "t": None}, "ic": {"mean": None, "t": None},
                "top": {"mean": None, "t": None}, "bottom": {"mean": None, "t": None}}


def family(data_dir):
    combined, status = {}, {}
    for model in MODELS:
        path = os.path.join(data_dir, "l46_%s_result.json" % model)
        doc = json.load(open(path)) if os.path.exists(path) else None
        ok = bool(doc and doc.get("status") == "DONE")
        status[model] = doc.get("status") if doc else "NOT RUN"
        for h in k.HORIZONS:
            combined["%s:%s" % (model, h)] = doc["result"]["summaries"][h] if ok else VOID_SUMMARY
    assert len(combined) == N_TESTS_IN_FAMILY
    return {"status": status, "verdicts": k.gate(combined), "summaries": combined}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    args = ap.parse_args(argv)
    out = family(args.data_dir)
    path = os.path.join(args.data_dir, "l46_family_gate.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    for key, v in out["verdicts"].items():
        s = out["summaries"][key]["spread"]
        print("%-18s spread %s bp (t %s)  %s" % (key, None if s["mean"] is None else round(s["mean"], 1),
                                                 None if s["t"] is None else round(s["t"], 2), "PASS" if v["passes"] else "fail"))
    print("models:", out["status"])
    print("wrote", path)


if __name__ == "__main__":
    main()
