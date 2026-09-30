"""Research look L46: the parts of the family harness that decide something, testable
without torch or any model package."""
from research import tsfm_family_ic as f


def test_the_latest_revision_before_the_cutoff_is_used_and_the_window_is_kept():
    commits = [("a", "2025-06-30T10:00:00+00:00"), ("b", "2025-08-17T12:00:00+00:00"), ("c", "2025-09-09T09:00:00+00:00")]
    sessions = ["2025-09-01", "2025-09-02", "2025-12-23"]
    sha, date, kept, moved = f.pick_family_revision(commits, sessions)
    assert (sha, kept, moved) == ("b", sessions, None)


def test_with_no_revision_before_the_cutoff_the_earliest_is_used_and_sessions_start_after_it():
    commits = [("late", "2025-11-01T00:00:00+00:00"), ("first", "2025-09-02T00:00:00+00:00")]
    sessions = ["2025-09-01", "2025-09-02", "2025-09-03", "2025-10-01"]
    sha, date, kept, moved = f.pick_family_revision(commits, sessions)
    assert sha == "first" and kept == ["2025-09-03", "2025-10-01"]
    assert moved == {"start": "2025-09-02", "sessions": 2, "void": True}


def test_six_models_three_horizons_eighteen_tests():
    assert len(f.MODELS) == 6 and f.N_TESTS_IN_FAMILY == 18
    assert set(f.ADAPTERS) == set(f.MODELS)


def test_the_module_imports_no_model_package_at_import_time():
    import ast
    tree = ast.parse(open(f.__file__).read())
    top = set()
    for node in tree.body:                      # module level only; adapters import inside methods
        if isinstance(node, ast.Import):
            top |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            top.add(node.module.split(".")[0])
    assert not top & {"torch", "chronos", "timesfm", "uni2ts", "tsfm_public", "tirex", "transformers", "numpy", "huggingface_hub"}


def test_the_family_gate_runs_bh_over_eighteen_with_voids_at_p_one(tmp_path):
    import json
    from research import l46_family_gate as g
    good = {"sessions": 79, "spread": {"mean": 40.0, "t": 5.0, "p": 1e-6, "halves": [{"mean": 30.0}, {"mean": 50.0}]},
            "pic": {"mean": 0.05, "t": 3.0}, "ic": {"mean": 0.05, "t": 3.0},
            "top": {"mean": 20.0, "t": 3.0}, "bottom": {"mean": -20.0, "t": -3.0}}
    doc = {"status": "DONE", "result": {"summaries": {"f15": good, "f30": good, "f60": good}}}
    (tmp_path / "l46_chronos_bolt_result.json").write_text(json.dumps(doc))
    out = g.family(str(tmp_path))
    assert len(out["verdicts"]) == 18
    assert out["verdicts"]["chronos_bolt:f15"]["passes"]
    assert not out["verdicts"]["sundial:f60"]["passes"] and out["status"]["sundial"] == "NOT RUN"


def test_only_revisions_that_hold_weights_are_candidates():
    commits = [("readme", "2025-09-02T01:00:00+00:00"), ("weights", "2025-09-02T05:00:00+00:00"), ("later", "2025-09-12T00:00:00+00:00")]
    files = {"readme": ["README.md", ".gitattributes"], "weights": ["config.json", "model.safetensors"], "later": ["model.safetensors"]}
    usable = f.with_weights("x/y", commits, list_files=lambda sha: files[sha])
    assert [c[0] for c in usable] == ["weights", "later"]
    sha, _, kept, moved = f.pick_family_revision(usable, ["2025-09-01", "2025-09-03"])
    assert sha == "weights" and kept == ["2025-09-03"] and moved["start"] == "2025-09-02"
