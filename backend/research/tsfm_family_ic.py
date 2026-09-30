"""Research look L46 — six zero-shot time-series foundation models in the L40 harness.

Pre-registered: docs/research/prereg-tsfm-family.md (commit 6921f08), before this file
was written and before any of these models was run. The harness is L40's: samples,
targets, m60, per-session statistics and the gate come from kronos_feature_ic, so the
only thing that differs between L40 and a model here is the forecaster.

One model per process, because their packages conflict and each gets its own
environment on the PC:

    python -m research.tsfm_family_ic --model chronos_bolt --stage0-only
    python -m research.tsfm_family_ic --model chronos_bolt

Revisions (prereg §2): the latest revision dated before 2025-09-01; if none exists,
the EARLIEST revision is used and the model's sessions start after its date (void if
fewer than 60 remain). L40's own code would have taken the latest revision in that
case; the look never needed it, and the prereg's words are followed here.

Nothing in the live path imports this (tests/test_research_splits.py). torch and every
model package are imported inside the adapters only.
"""
import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from research import kronos_feature_ic as k  # noqa: E402
from research import splits  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(BACKEND), "docs", "research", "data")
SEED = k.SEED
PRED_LEN = k.PRED_LEN
N_TESTS_IN_FAMILY = 18            # six models x three horizons (prereg §4)
SUNDIAL_SAMPLES = 3

MODELS = {
    "chronos_bolt": {"repo": "amazon/chronos-bolt-base", "output": "median quantile"},
    "timesfm_2p5": {"repo": "google/timesfm-2.5-200m-pytorch", "output": "point forecast"},
    "moirai_2": {"repo": "Salesforce/moirai-2.0-R-small", "output": "median quantile"},
    "flowstate": {"repo": "ibm-granite/granite-timeseries-flowstate-r1", "output": "median quantile"},
    "tirex": {"repo": "NX-AI/TiRex", "output": "median quantile"},
    "sundial": {"repo": "thuml/sundial-base-128m", "output": "mean of 3 samples"},
}


WEIGHT_SUFFIXES = (".safetensors", ".bin", ".ckpt", ".pth")


def with_weights(repo, commits, list_files=None):
    """The commits whose file list holds model weights (amendment 1: an initial commit
    with only a README is not a model)."""
    if list_files is None:
        from huggingface_hub import HfApi
        api = HfApi()
        list_files = lambda sha: api.list_repo_files(repo, revision=sha)  # noqa: E731
    return [c for c in commits if any(f.endswith(WEIGHT_SUFFIXES) for f in list_files(c[0]))]


def pick_family_revision(commits, sessions):
    """(sha, date, sessions kept, moved info). commits: [(sha, iso date)], already
    restricted to revisions that hold weights."""
    before = k.pick_revision(commits)
    if before:
        return before[0], before[1], sessions, None
    earliest = min(commits, key=lambda c: c[1])
    start = earliest[1][:10]
    kept = [s for s in sessions if s > start]
    moved = {"start": start, "sessions": len(kept), "void": len(kept) < k.MIN_SESSIONS_IF_MOVED}
    return earliest[0], earliest[1], kept, moved


def closes(window):
    return [float(b["close"]) for b in window]


def set_seeds(seed=SEED):
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---- adapters: each maps a list of 512-bar windows to a list of PRED_LEN closes --------

class Forecaster:
    name = None

    def __init__(self, local_dir, device):
        self.local_dir, self.device = local_dir, device

    def forecast_batch(self, windows):
        raise NotImplementedError

    def smoke(self):
        """Prereg stage 0 step 1: the documented call on a synthetic series returns
        finite values of the right shape."""
        import math
        base = [100.0 + 2.0 * math.sin(i / 7.0) + 0.01 * i for i in range(k.LOOKBACK)]
        win = [{"close": v, "open": v, "high": v, "low": v, "volume": 1000, "time": "2025-01-01T09:15:00"} for v in base]
        out = self.forecast_batch([win, win])
        ok = len(out) == 2 and all(len(o) == PRED_LEN and all(math.isfinite(x) for x in o) for o in out)
        return {"ok": ok, "first": [round(x, 4) for x in out[0][:4]]}


class ChronosBolt(Forecaster):
    name = "chronos_bolt"

    def __init__(self, local_dir, device):
        super().__init__(local_dir, device)
        import torch
        from chronos import BaseChronosPipeline
        self.torch = torch
        self.pipe = BaseChronosPipeline.from_pretrained(local_dir, device_map=device, torch_dtype=torch.float32)

    def forecast_batch(self, windows):
        ctx = [self.torch.tensor(closes(w), dtype=self.torch.float32) for w in windows]
        q, _mean = self.pipe.predict_quantiles(ctx, prediction_length=PRED_LEN, quantile_levels=[0.5])
        return [row[:, 0].tolist() for row in q.cpu()]


class TimesFM25(Forecaster):
    name = "timesfm_2p5"

    def __init__(self, local_dir, device):
        super().__init__(local_dir, device)
        import numpy as np
        import timesfm
        import timesfm.timesfm_2p5.timesfm_2p5_torch as tt
        import torch
        self.np = np
        # Amendment 2: the published checkpoints store query, key and value separately;
        # the current code fuses them into one projection and splits its output in that
        # order (torch.chunk(qkv, 3) -> query, key, value). Concatenating the three
        # weight matrices in the same order is an exact rearrangement.
        original = tt.load_file

        def fused(path):
            t = original(path)
            for key in [n for n in t if n.endswith(".attn.query.weight")]:
                pre = key[: -len("query.weight")]
                for kind in ("weight", "bias"):
                    if pre + "query." + kind in t:
                        t[pre + "qkv_proj." + kind] = torch.cat([t.pop(pre + "query." + kind), t.pop(pre + "key." + kind),
                                                                 t.pop(pre + "value." + kind)], 0)
            return t
        tt.load_file = fused
        # torch.compile needs Triton, which Windows lacks; run the same graph eagerly.
        import torch._dynamo
        torch._dynamo.config.disable = True
        self.model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(local_dir)
        self.model.compile(timesfm.ForecastConfig(max_context=k.LOOKBACK, max_horizon=128, normalize_inputs=True,
                                                  use_continuous_quantile_head=True, force_flip_invariance=True,
                                                  infer_is_positive=True, fix_quantile_crossing=True))

    def forecast_batch(self, windows):
        point, _q = self.model.forecast(horizon=PRED_LEN, inputs=[self.np.array(closes(w), dtype=self.np.float32) for w in windows])
        return [list(map(float, p[:PRED_LEN])) for p in point]


class Moirai2(Forecaster):
    name = "moirai_2"

    def __init__(self, local_dir, device):
        super().__init__(local_dir, device)
        import torch
        from uni2ts.model.moirai2 import Moirai2Forecast, Moirai2Module
        self.torch = torch
        self.model = Moirai2Forecast(module=Moirai2Module.from_pretrained(local_dir), prediction_length=PRED_LEN,
                                     context_length=k.LOOKBACK, target_dim=1, feat_dynamic_real_dim=0,
                                     past_feat_dynamic_real_dim=0).to(device)
        self.model.eval()

    def forecast_batch(self, windows):
        t = self.torch.tensor([closes(w) for w in windows], dtype=self.torch.float32, device=self.device).unsqueeze(-1)
        observed = self.torch.ones_like(t, dtype=self.torch.bool)
        pad = self.torch.zeros(t.shape[:2], dtype=self.torch.bool, device=self.device)
        with self.torch.no_grad():
            out = self.model(past_target=t, past_observed_target=observed, past_is_pad=pad)
        # out: [batch, quantiles, prediction_length] (median is the middle quantile)
        qs = self.model.module.quantile_levels if hasattr(self.model.module, "quantile_levels") else None
        mid = qs.index(0.5) if qs and 0.5 in qs else out.shape[1] // 2
        return [row[mid, :PRED_LEN].float().cpu().tolist() for row in out]


class FlowState(Forecaster):
    name = "flowstate"
    SCALE_FACTOR = 1.0

    def __init__(self, local_dir, device):
        super().__init__(local_dir, device)
        import torch
        from tsfm_public import FlowStateForPrediction
        self.torch = torch
        self.model = FlowStateForPrediction.from_pretrained(local_dir).to(device)
        self.model.eval()

    def forecast_batch(self, windows):
        t = self.torch.tensor([closes(w) for w in windows], dtype=self.torch.float32, device=self.device).unsqueeze(-1)
        with self.torch.no_grad():
            out = self.model(past_values=t, scale_factor=self.SCALE_FACTOR, prediction_length=PRED_LEN, batch_first=True)
        pred = out.quantile_outputs            # [batch, quantiles, prediction_length, channels]
        mid = list(self.model.config.quantiles).index(0.5)
        return [row[mid, :PRED_LEN, 0].float().cpu().tolist() for row in pred]


class TiRex(Forecaster):
    name = "tirex"

    def __init__(self, local_dir, device):
        super().__init__(local_dir, device)
        import torch
        from tirex import load_model
        self.torch = torch
        revision = os.path.basename(os.path.normpath(local_dir))     # the snapshot folder is the revision
        self.model = load_model(MODELS["tirex"]["repo"], device=device, backend="torch", hf_kwargs={"revision": revision})

    def forecast_batch(self, windows):
        ctx = self.torch.tensor([closes(w) for w in windows], dtype=self.torch.float32)
        quantiles, _mean = self.model.forecast(context=ctx, prediction_length=PRED_LEN)
        mid = quantiles.shape[-1] // 2        # [batch, prediction_length, 9 quantiles]
        return [row[:PRED_LEN, mid].float().cpu().tolist() for row in quantiles]


class Sundial(Forecaster):
    name = "sundial"

    def __init__(self, local_dir, device):
        super().__init__(local_dir, device)
        import torch
        from transformers import AutoModelForCausalLM
        self.torch = torch
        self.model = AutoModelForCausalLM.from_pretrained(local_dir, trust_remote_code=True).to(device)
        self.model.eval()

    def forecast_batch(self, windows):
        set_seeds()
        t = self.torch.tensor([closes(w) for w in windows], dtype=self.torch.float32, device=self.device)
        with self.torch.no_grad():
            out = self.model.generate(t, max_new_tokens=PRED_LEN, num_samples=SUNDIAL_SAMPLES)
        # out: [batch, num_samples, prediction_length]
        return [row.float().mean(dim=0)[:PRED_LEN].cpu().tolist() for row in out]


ADAPTERS = {c.name: c for c in (ChronosBolt, TimesFM25, Moirai2, FlowState, TiRex, Sundial)}


class Wrapped:
    """Seeds before every batch, as L40's forecaster does, so the lookahead check and
    the pass see the same random stream for the generative model."""

    def __init__(self, inner):
        self.inner = inner
        self.sample_count = 1

    def forecast_batch(self, windows):
        set_seeds()
        return self.inner.forecast_batch(windows)


# ---- the run -------------------------------------------------------------------------

def _paths(model):
    return (os.path.join(OUT_DIR, "l46_%s_stage0.json" % model), os.path.join(OUT_DIR, "l46_%s_result.json" % model),
            os.path.join(HERE, "l46_rows_%s.jsonl" % model))


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


def environment(model):
    import platform
    out = {"python": sys.version.split()[0], "machine": platform.machine(), "platform": platform.platform()}
    for name in ("torch", "numpy", "transformers", "chronos", "timesfm", "uni2ts", "tsfm_public", "tirex", "huggingface_hub"):
        try:
            mod = __import__(name)
            out[name] = getattr(mod, "__version__", "installed")
        except Exception:
            pass
    try:
        import torch
        out["cuda"] = torch.cuda.is_available()
        out["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        pass
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", required=True, choices=sorted(MODELS))
    ap.add_argument("--stage0-only", action="store_true")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--smoke", action="store_true", help="load the pinned revision and forecast a synthetic series; reads no project data")
    args = ap.parse_args(argv)
    model = args.model
    if args.smoke:
        from huggingface_hub import HfApi, snapshot_download
        commits = [(c.commit_id, c.created_at.isoformat()) for c in HfApi().list_repo_commits(MODELS[model]["repo"])]
        sha, date, _, moved = pick_family_revision(with_weights(MODELS[model]["repo"], commits), [])
        inner = ADAPTERS[model](snapshot_download(MODELS[model]["repo"], revision=sha), args.device)
        print(json.dumps({"model": model, "revision": [sha, date], "moved": moved, "smoke": inner.smoke(),
                          "environment": environment(model)}), flush=True)
        return
    stage0_path, result_path, rows_path = _paths(model)
    import kite_history
    db = os.environ.get("KRONOS_CANDLE_DB")
    if db:
        from pathlib import Path
        kite_history.DB_PATH = Path(db)

    stage0 = {"look": "L46", "model": model, "repo": MODELS[model]["repo"], "output_used": MODELS[model]["output"],
              "started": datetime.now().isoformat(), "argv": sys.argv[1:], "prereg": "docs/research/prereg-tsfm-family.md",
              "environment": environment(model)}

    def halt(step, why):
        stage0["halted_at"] = {"step": step, "why": why}
        _write(stage0_path if args.stage0_only else result_path, {"stage0": stage0, "status": "VOID"})
        print("VOID at stage 0 step %s: %s" % (step, why), flush=True)
        sys.exit(2)

    rows = k.load_membership_rows()
    members = sorted({r["symbol"] for r in rows})
    pre = kite_history.load_batch(members, interval="5m")
    sessions = k.selection_sessions(splits.sessions_in(pre))
    stage0["selection"] = splits.describe_split("selection", sessions)

    # step 2: revisions
    from huggingface_hub import HfApi, snapshot_download
    commits = [(c.commit_id, c.created_at.isoformat()) for c in HfApi().list_repo_commits(MODELS[model]["repo"])]
    usable = with_weights(MODELS[model]["repo"], commits)
    sha, date, sessions, moved = pick_family_revision(usable, sessions)
    stage0["revisions"] = {"commits": commits, "with_weights": [c[0] for c in usable], "picked": [sha, date], "moved_window": moved}
    if moved and moved["void"]:
        halt(2, "no revision predates %s and only %d sessions remain after %s" % (k.REVISION_CUTOFF, moved["sessions"], moved["start"]))
    local_dir = snapshot_download(MODELS[model]["repo"], revision=sha)

    # step 1: the model runs as documented
    try:
        inner = ADAPTERS[model](local_dir, args.device)
        stage0["smoke"] = inner.smoke()
    except Exception as exc:
        halt(1, "the model did not load or run: %r" % (exc,))
    if not stage0["smoke"]["ok"]:
        halt(1, "the documented call returned the wrong shape or non-finite values")
    fc = Wrapped(inner)

    members_by_date = {d: k.membership_asof(rows, d) for d in sessions}
    flat_by_sym = {s: sorted(c, key=lambda x: x["time"]) for s, c in pre.items()}
    sessions_by_sym = {s: k.by_session(c) for s, c in flat_by_sym.items()}
    dropped = k.stage0_adjustment(stage0, kite_history, list(flat_by_sym), sessions)
    samples = k.build_samples(flat_by_sym, sessions_by_sym, sessions, members_by_date, dropped)
    pool = [(s[0], s[3]) for s in samples]

    k.halt = lambda st0, step, why: halt(step, why)
    k.stage0_lookahead(stage0, fc, flat_by_sym, pool)

    # step 4: timing, for information
    rng = random.Random(SEED + 1)
    picks = rng.sample(pool, min(200, len(pool)))
    windows = [k.lookback_window(flat_by_sym[s], i) for s, i in picks]
    started = time.time()
    for i in range(0, len(windows), 25):
        fc.forecast_batch(windows[i:i + 25])
    per = (time.time() - started) / max(len(windows), 1)
    stage0["timing"] = {"forecasts": len(windows), "seconds_per": per, "est_hours_total": per * len(samples) / 3600}

    per_session = defaultdict(int)
    for s in samples:
        per_session[s[1]] += 1
    k.stage0_coverage(stage0, sessions, per_session)
    stage0["samples"] = len(samples)
    _write(stage0_path, {"stage0": stage0, "status": "STAGE0_DONE"})
    print("stage 0 complete: %s, %d samples over %d sessions, %.3f s a forecast" % (model, len(samples), len(sessions), per), flush=True)
    if args.stage0_only:
        return

    k.ROWS = rows_path
    k.run_ic_pass(fc, samples, flat_by_sym, sessions_by_sym, progress=k._progress)
    result = k.evaluate_rows(rows_path)
    _write(result_path, {"stage0": stage0, "status": "DONE", "finished": datetime.now().isoformat(), "result": result,
                         "constants": {"two_leg_bp": k.TWO_LEG_BP, "round_trip_bp": k.ROUND_TRIP_BP,
                                       "family_tests": N_TESTS_IN_FAMILY, "bh_q": k.BH_Q}})
    for name, s in result["summaries"].items():
        sp, ic, pic = s["spread"], s["ic"], s["pic"]
        print("%s %s: sessions %d | IC %.4f (t %.2f) | partial IC %.4f (t %.2f) | spread %.1f bp (t %.2f)"
              % (model, name, s["sessions"], ic["mean"] or 0, ic["t"] or 0, pic["mean"] or 0, pic["t"] or 0,
                 sp["mean"] or 0, sp["t"] or 0), flush=True)
    print("wrote", result_path, flush=True)


if __name__ == "__main__":
    main()
