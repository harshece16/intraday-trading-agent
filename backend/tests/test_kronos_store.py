"""
The Kronos space (README section 102): the store that reads the shadow's and the
L40 pass's JSON files into backend/data/kronos.db, and the two routes that show it.

What matters here: a day file rewritten with targets filled in updates the rows
already stored; a file caught mid-write is skipped this time and read next time;
the look's records come through whole and summarise without breaking on a missing
field; and the store stays what it claims to be: read by two display routes and
by nothing in the engine (rule RES-32).
"""
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import kronos_store

BACKEND = Path(__file__).parent.parent
STOCKS = ("RELIANCE", "HDFCBANK", "TCS")


def _row(date, hhmm, symbol, i, targets):
    return {
        "date": date, "hhmm": hhmm, "symbol": symbol, "computed_at": f"{date}T{hhmm}:20+05:30",
        "c0": 1000.0 + i, "pred_close": [1000.0 + i + k * 0.5 for k in range(12)],
        "features": {"f15": -18.3 + i, "f30": 22.2 + i, "f60": 130.0 - i}, "m60": -31.1 + i,
        "bars_delayed": i % 2 == 1, "kite_active": True,
        "scanner": {"side": "SHORT" if i % 2 else "LONG", "score": 81.6, "final_score": 96.6, "ltp": 1182.0,
                    "gap_pct": -0.32, "rvol": 2.1, "feed": "live"},
        "targets": targets,
    }


def _running():
    block = {"n": 2, "mean": 0.12, "t": 1.4, "se": 0.08, "p": 0.3, "pct_pos": 1.0}
    return {h: {"times": 2, "ic": dict(block), "pic": dict(block, mean=0.05), "spread": dict(block, mean=40.5),
                "top": dict(block, mean=10.0), "bottom": dict(block, mean=-30.5)} for h in ("f15", "f30", "f60")}


def _day_doc(date, times=("09:45", "10:00"), targets=None):
    rows = []
    for j, hhmm in enumerate(times):
        for i, sym in enumerate(STOCKS):
            rows.append(_row(date, hhmm, sym, i + 10 * j, targets))
    return {"date": date, "sample_count": 3, "device": "cpu", "updated": f"{date}T{times[-1]}:25+05:30",
            "rows": rows, "running": _running() if targets else {}}


def _summary_doc(date):
    return {"date": date, "rows": 6, "stocks": 3, "times": 2, "bars": {"live": 4, "delayed": 2},
            "sample_count": 3, "device": "cpu",
            "share_of_forecasts_on_the_scanners_side": {"f15": 0.5, "f30": 0.5, "f60": 0.67},
            "stats": _running(), "note": "One session. Recorded, not concluded from."}


def _stage0_doc(machine="arm64"):
    return {"status": "STAGE0_DONE",
            "stage0": {"started": "2026-09-29T20:32:42", "argv": ["--device", "cpu", "--stage0-only"],
                       "selection": "selection: 79 sessions, 2025-09-01 to 2025-12-23",
                       "regression": {"result": "PASS", "seconds": 20, "tail": "4 passed"},
                       "revisions": {"NeoQuasar/Kronos-small": {"commits": [], "picked": ["12b79908b3a9bef4", "2025-08-17T12:06:18+00:00"]},
                                     "NeoQuasar/Kronos-Tokenizer-base": {"commits": [], "picked": ["f6c7de7b0490e422", "2025-08-17T12:06:41+00:00"]}},
                       "lookahead": [{"symbol": "X", "idx": i, "identical": True} for i in range(20)],
                       "timing": {"seconds_per": 5.2, "est_hours_at_sample_count_3": 62.6, "sample_count_chosen": 1},
                       "adjustment": {"dropped_count": 0},
                       "coverage": {"sessions": 79, "first_half": 39, "second_half": 40, "stock_times": 43362}},
            "harness": {"device": "cpu", "threads": 4, "torch": "2.8.0", "python": "3.9.6", "machine": machine}}


def _result_doc():
    def block(mean, t, halves=(1.0, 1.0)):
        return {"n": 79, "mean": mean, "t": t, "se": 0.1, "p": 0.2, "pct_pos": 0.55,
                "halves": [{"mean": halves[0]}, {"mean": halves[1]}]}
    summaries = {
        "f15": {"sessions": 79, "ic": block(0.01, 0.8), "pic": block(0.0, 0.1), "spread": block(5.0, 0.9),
                "top": block(-2.0, -0.5), "bottom": block(-7.0, -1.1)},
        "f30": {"sessions": 79, "ic": block(0.02, 1.1), "pic": block(0.01, 0.6), "spread": block(12.0, 1.5, (14.0, -3.0)),
                "top": block(1.0, 0.2), "bottom": block(-11.0, -1.6)},
    }
    gate = {"f15": {"passes": False, "checks": {"spread_gt_two_leg": False, "spread_t_gt_2": False, "sessions_ge_min": True,
                                                 "both_halves_positive": True, "bh_survives": False, "partial_ic_t_gt_2": False},
                    "single_side_note": {"top": False, "bottom": False}},
            "f30": {"passes": False, "checks": {"spread_gt_two_leg": False, "spread_t_gt_2": False, "sessions_ge_min": True,
                                                 "both_halves_positive": False, "bh_survives": False, "partial_ic_t_gt_2": False},
                    "single_side_note": {"top": False, "bottom": False}}}
    return {"status": "DONE", "finished": "2026-10-02T03:10:00", "result": {"summaries": summaries, "gate": gate},
            "constants": {"two_leg_bp": 33.26, "round_trip_bp": 16.63, "bh_q": 0.10}}


@pytest.fixture
def store(tmp_path, monkeypatch):
    data = tmp_path / "data"
    docs = tmp_path / "docs"
    data.mkdir()
    docs.mkdir()
    monkeypatch.setattr(kronos_store, "DATA_DIR", data)
    monkeypatch.setattr(kronos_store, "DOCS_DATA_DIR", docs)
    monkeypatch.setattr(kronos_store, "DB_PATH", tmp_path / "kronos.db")
    return {"data": data, "docs": docs, "db": tmp_path / "kronos.db"}


def _write(path, doc):
    path.write_text(json.dumps(doc))


# ---- shadow files ---------------------------------------------------------


def test_ingests_a_shadow_day_and_its_summary(store):
    _write(store["data"] / "kronos_shadow_2026-09-30.json", _day_doc("2026-09-30"))
    _write(store["data"] / "kronos_shadow_2026-09-30_summary.json", _summary_doc("2026-09-30"))
    # Not a day: the shadow's dry-run file carries "test" in its name and must stay out.
    _write(store["data"] / "kronos_shadow_test_2026-09-29.json", _day_doc("2026-09-29"))

    found = kronos_store.ingest_shadow_files()
    assert found == {"days": 1, "rows": 6, "summaries": 1, "skipped": []}

    day = kronos_store.shadow_day("2026-09-30")
    assert day["rows"] == 6 and day["stocks"] == 3 and day["times"] == 2
    assert day["bars_live"] == 4 and day["bars_delayed"] == 2         # counted from the rows
    assert day["hhmm_list"] == ["09:45", "10:00"] and day["latest_hhmm"] == "10:00"
    assert day["summary"]["note"].startswith("One session")
    assert day["realised"] == 0
    first = [r for r in day["forecasts"] if r["hhmm"] == "09:45" and r["symbol"] == "RELIANCE"][0]
    assert first["f15"] == pytest.approx(-18.3) and first["f60"] == pytest.approx(130.0)
    assert first["scanner"]["side"] == "LONG" and first["bars_delayed"] is False
    assert first["targets"] is None and len(first["pred_close"]) == 12

    days = kronos_store.shadow_days()
    assert [d["date"] for d in days] == ["2026-09-30"]
    assert days[0]["ic"]["f15"]["mean"] == pytest.approx(0.12)       # from the summary's stats
    assert days[0]["agreement"]["f60"] == pytest.approx(0.67)
    assert kronos_store.shadow_day("2026-09-29") is None


def test_targets_filled_later_overwrite_the_nulls(store):
    path = store["data"] / "kronos_shadow_2026-09-30.json"
    _write(path, _day_doc("2026-09-30", targets={"f15": None, "f30": None, "f60": None}))
    kronos_store.ingest_shadow_files()
    assert kronos_store.shadow_day("2026-09-30")["realised"] == 0

    # The shadow rewrites the same file once the bars after each time have closed.
    _write(path, _day_doc("2026-09-30", targets={"f15": 35.1, "f30": -13.9, "f60": -55.6}))
    kronos_store.ingest_shadow_files()

    day = kronos_store.shadow_day("2026-09-30")
    assert day["realised"] == 6 and len(day["forecasts"]) == 6         # updated, not duplicated
    assert day["forecasts"][0]["targets"] == {"f15": 35.1, "f30": -13.9, "f60": -55.6}
    assert day["running"]["f60"]["ic"]["t"] == pytest.approx(1.4)
    assert kronos_store.shadow_days()[0]["ic"]["f60"]["times"] == 2   # no summary yet: from the running stats


def test_a_half_written_file_is_skipped_this_time_and_read_next_time(store):
    good = store["data"] / "kronos_shadow_2026-09-29.json"
    torn = store["data"] / "kronos_shadow_2026-09-30.json"
    _write(good, _day_doc("2026-09-29"))
    torn.write_text(json.dumps(_day_doc("2026-09-30"))[:200])           # caught mid-write

    found = kronos_store.ingest_shadow_files()
    assert found["skipped"] == ["kronos_shadow_2026-09-30.json"] and found["days"] == 1
    assert [d["date"] for d in kronos_store.shadow_days()] == ["2026-09-29"]

    _write(torn, _day_doc("2026-09-30"))
    assert kronos_store.ingest_shadow_files()["skipped"] == []
    assert [d["date"] for d in kronos_store.shadow_days()] == ["2026-09-30", "2026-09-29"]
    assert kronos_store.shadow_day()["date"] == "2026-09-30"           # the latest, when no date is given


def test_a_summary_alone_makes_a_day_and_a_later_day_file_keeps_it(store):
    _write(store["data"] / "kronos_shadow_2026-09-30_summary.json", _summary_doc("2026-09-30"))
    kronos_store.ingest_shadow_files()
    day = kronos_store.shadow_day("2026-09-30")
    assert day["rows"] == 6 and day["forecasts"] == [] and day["summary"]["stocks"] == 3

    _write(store["data"] / "kronos_shadow_2026-09-30.json", _day_doc("2026-09-30"))
    kronos_store.ingest_shadow_files()
    day = kronos_store.shadow_day("2026-09-30")
    assert len(day["forecasts"]) == 6 and day["summary"]["stocks"] == 3  # neither file blanks the other


# ---- the look's records ---------------------------------------------------


def test_ingests_the_look_records_and_summarises_them(store):
    _write(store["docs"] / "kronos_l40_stage0.json", _stage0_doc("arm64"))
    _write(store["docs"] / "kronos_l40_stage0_pc.json", _stage0_doc("AMD64"))

    assert kronos_store.ingest_run_files() == {"runs": ["l40_stage0", "l40_stage0_pc"], "skipped": []}
    records = kronos_store.runs()
    assert [r["name"] for r in records] == ["l40_result", "l40_stage0", "l40_stage0_pc"][1:]
    assert records[0]["payload"]["stage0"]["coverage"]["sessions"] == 79   # stored whole
    assert records[0]["recorded_at"] == "2026-09-29T20:32:42"
    assert records[0]["source_path"] == "docs/research/data/kronos_l40_stage0.json"

    look = kronos_store.look_summary(records)
    assert look["result"] is None
    mac, pc = look["stage0"]
    assert (mac["machine"], pc["machine"]) == ("arm64", "AMD64")
    assert mac["regression"] == "PASS" and mac["regression_seconds"] == 20
    assert mac["lookahead_identical"] == 20 and mac["lookahead_n"] == 20
    assert mac["seconds_per_forecast"] == pytest.approx(5.2) and mac["sample_count_chosen"] == 1
    assert (mac["sessions"], mac["first_half"], mac["second_half"], mac["stock_times"]) == (79, 39, 40, 43362)
    assert mac["revisions"] == [{"repo": "NeoQuasar/Kronos-small", "commit": "12b79908", "date": "2025-08-17"},
                                {"repo": "NeoQuasar/Kronos-Tokenizer-base", "commit": "f6c7de7b", "date": "2025-08-17"}]


def test_the_result_is_summarised_per_horizon_and_a_missing_field_does_not_break_it(store):
    _write(store["docs"] / "kronos_l40_result.json", _result_doc())
    kronos_store.ingest_run_files()
    look = kronos_store.look_summary(kronos_store.runs())
    result = look["result"]
    assert result["status"] == "DONE" and result["constants"]["two_leg_bp"] == 33.26
    assert sorted(result["horizons"]) == ["f15", "f30"]                # f60 absent from the record: left out, not invented
    f30 = result["horizons"]["f30"]
    assert f30["spread"]["mean"] == 12.0 and f30["spread"]["halves"] == [14.0, -3.0]
    assert f30["passes"] is False and f30["checks"]["both_halves_positive"] is False

    # A record with nothing but a status must still summarise.
    _write(store["docs"] / "kronos_l40_result.json", {"status": "RUNNING"})
    _write(store["docs"] / "kronos_l40_stage0.json", {"status": "STAGE0_RUNNING"})
    kronos_store.ingest_run_files()
    look = kronos_store.look_summary(kronos_store.runs())
    assert look["result"]["horizons"] == {} and look["result"]["status"] == "RUNNING"
    assert look["stage0"][0]["lookahead_n"] == 0 and look["stage0"][0]["revisions"] == []


def test_a_half_written_record_is_skipped_this_time(store):
    (store["docs"] / "kronos_l40_result.json").write_text('{"status": "DONE", "result": {')
    assert kronos_store.ingest_run_files() == {"runs": [], "skipped": ["kronos_l40_result.json"]}
    assert kronos_store.runs() == []


# ---- the routes -----------------------------------------------------------
#
# app.py cannot be imported in a test: importing it builds the engine. The two
# route bodies are one call each into kronos_store, so the same two handlers are
# mounted on a bare FastAPI app here, and the test after this one checks that
# app.py declares exactly those routes, calling exactly those functions.


def _stub_app():
    app = FastAPI()

    @app.get("/api/kronos")
    def kronos_page():
        return kronos_store.page(today="2026-09-30")

    @app.get("/api/kronos/day/{date}")
    def kronos_day(date: str):
        day = kronos_store.day_page(date)
        if day is None:
            raise HTTPException(status_code=404, detail="no such day")
        return day

    return app


def test_the_page_route_ingests_on_request_and_the_day_route_serves_one_day(store):
    client = TestClient(_stub_app())

    empty = client.get("/api/kronos").json()
    assert empty == {"look": {"stage0": [], "result": None}, "today": None, "date_today": "2026-09-30", "days": [],
                     "prereg": "docs/research/prereg-kronos-feature-ic.md"}

    # Files appear while the process runs; the next request shows them, no restart.
    _write(store["data"] / "kronos_shadow_2026-09-29.json", _day_doc("2026-09-29"))
    _write(store["data"] / "kronos_shadow_2026-09-30.json", _day_doc("2026-09-30", targets={"f15": 1.0, "f30": 2.0, "f60": 3.0}))
    _write(store["docs"] / "kronos_l40_stage0.json", _stage0_doc())

    page = client.get("/api/kronos").json()
    assert page["today"]["date"] == "2026-09-30" and page["today"]["realised"] == 6
    assert [d["date"] for d in page["days"]] == ["2026-09-30", "2026-09-29"]
    assert page["look"]["stage0"][0]["sessions"] == 79 and page["look"]["result"] is None

    day = client.get("/api/kronos/day/2026-09-29").json()
    assert day["date"] == "2026-09-29" and len(day["forecasts"]) == 6 and day["realised"] == 0
    assert client.get("/api/kronos/day/2026-01-01").status_code == 404
    assert client.get("/api/kronos/day/not-a-date").status_code == 404


def test_the_page_falls_back_to_the_latest_day_when_today_has_none(store):
    _write(store["data"] / "kronos_shadow_2026-09-26.json", _day_doc("2026-09-26"))
    assert kronos_store.page(today="2026-09-30")["today"]["date"] == "2026-09-26"


def _routes_in_app_py():
    """{path: names the handler calls on kronos_store} for every /api/kronos route in app.py."""
    tree = ast.parse((BACKEND / "app.py").read_text())
    routes = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "get"
                    and dec.args and isinstance(dec.args[0], ast.Constant) and str(dec.args[0].value).startswith("/api/kronos")):
                calls = {n.func.attr for n in ast.walk(node)
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and isinstance(n.func.value, ast.Name) and n.func.value.id == "kronos_store"}
                routes[dec.args[0].value] = calls
    return routes


def test_app_declares_the_two_routes_and_they_only_read():
    routes = _routes_in_app_py()
    assert routes == {"/api/kronos": {"page"}, "/api/kronos/day/{date}": {"day_page"}}


# ---- the boundary (rule RES-32) ------------------------------------------


def _imports(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_nothing_in_the_engine_imports_the_store():
    """The store is display data. Only app.py may import it, for its two routes;
    the scanner, the brain, the risk manager and the engine never see it."""
    importers = sorted(p.name for p in list(BACKEND.glob("*.py")) + list((BACKEND / "strategies").rglob("*.py"))
                       if p.name != "kronos_store.py" and "kronos_store" in _imports(p))
    assert importers == ["app.py"]


def test_the_store_stays_off_the_research_and_torch_path():
    names = _imports(BACKEND / "kronos_store.py")
    assert not names & {"research", "torch", "numpy", "pandas", "huggingface_hub"}, names
