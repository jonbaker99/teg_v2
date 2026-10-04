"""TEGBot toolkit: zips, skills, import without PyGithub, sim.py and tegstats."""
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from teg_analysis.chatbot import toolkit as tk

REPO = Path(__file__).resolve().parents[1]
SIM = REPO / "teg_analysis/chatbot/toolkit/skills/teg-simulation/scripts"
STATS = REPO / "teg_analysis/chatbot/toolkit/skills/teg-analysis/scripts"
SMALL = ["--n-sims", "2000"]


@pytest.fixture(scope="module")
def extracted(tmp_path_factory):
    """Both zips unpacked the way the sandbox does it."""
    root = tmp_path_factory.mktemp("teg")
    for name, blob in ((tk.TOOLKIT_ZIP, tk.code_zip()), (tk.DATA_ZIP, tk.data_zip())):
        zipfile.ZipFile(io.BytesIO(blob)).extractall(root)
    return root


def _run(root, code, **kw):
    env = {**os.environ, "TEG_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PYTHONPATH", None)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env=env, cwd=str(root), **kw)


# ---------------------------------------------------------------- zips

def test_code_zip_is_deterministic_and_cached():
    assert tk.code_zip() == tk.code_zip()
    assert tk.data_zip() == tk.data_zip()


def test_code_zip_contents():
    names = zipfile.ZipFile(io.BytesIO(tk.code_zip())).namelist()
    assert names == sorted(names)
    assert "teg_analysis/analysis/simulation.py" in names
    assert not any(n.startswith(("teg_analysis/chatbot/", "teg_analysis/reporting/")) for n in names)
    assert not any("__pycache__" in n or n.endswith(".pyc") for n in names)
    for skill in ("teg-simulation", "teg-analysis"):
        assert f"skills/{skill}/SKILL.md" in names
    assert "skills/teg-simulation/scripts/sim.py" in names
    assert "skills/teg-analysis/scripts/tegstats.py" in names
    assert "skills/teg-analysis/reference/rules.md" in names


def test_data_zip_contents():
    names = zipfile.ZipFile(io.BytesIO(tk.data_zip())).namelist()
    for p in ("data/all-scores.parquet", "data/all-data.parquet", "data/players.csv",
              "data/handicaps.csv", "data/round_pars.csv", "data/course_pars.csv"):
        assert p in names


def test_skill_frontmatter_parses():
    found = tk.skills()
    assert {s["name"] for s in found} == {"teg-simulation", "teg-analysis"}
    for s in found:
        assert s["description"] and s["path"].startswith("/tmp/teg/skills/")


def test_skills_index_mentions_skills_and_setup():
    text = tk.skills_index()
    assert tk.SETUP_CMD in text
    assert "teg-simulation" in text and "teg-analysis" in text
    assert "/tmp/teg/skills/teg-simulation/SKILL.md" in text


def test_setup_cmd_extracts_both_zips(tmp_path):
    inp = tmp_path / "in"
    inp.mkdir()
    (inp / tk.TOOLKIT_ZIP).write_bytes(tk.code_zip())
    (inp / tk.DATA_ZIP).write_bytes(tk.data_zip())
    cmd = tk.SETUP_CMD.replace(tk.ROOT_IN_SANDBOX, str(tmp_path / "teg"))
    for _ in range(2):  # idempotent
        r = subprocess.run(["bash", "-c", cmd], env={**os.environ, "INPUT_DIR": str(inp)},
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "ready" in r.stdout
    assert (tmp_path / "teg/teg_analysis/__init__.py").exists()
    assert (tmp_path / "teg/data/players.csv").exists()


# ---------------------------------------------------------------- no PyGithub

def test_engine_runs_from_zip_without_pygithub(extracted):
    code = (
        "import sys; sys.modules['github'] = None\n"
        "import teg_analysis\n"
        f"sys.path.insert(0, {str(extracted / 'skills/teg-simulation/scripts')!r})\n"
        "import sim\n"
        "out = sim.baseline(n_sims=500)\n"
        "assert out['table'] and 'github' not in [m for m in sys.modules if sys.modules[m]]\n"
        "assert 'teg_analysis.chatbot' not in sys.modules\n"
        "print('OK', out['teg'])\n")
    r = _run(extracted, code)
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_package_imports_in_repo_without_pygithub():
    r = subprocess.run(
        [sys.executable, "-c", "import sys; sys.modules['github']=None; import teg_analysis.io, "
         "teg_analysis.analysis.simulation; print('OK')"],
        capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------- sim.py

@pytest.fixture(scope="module")
def sim(extracted):
    os.environ["TEG_ROOT"] = str(REPO)
    sys.path.insert(0, str(SIM))
    import sim as mod
    yield mod
    sys.path.remove(str(SIM))


def test_baseline_matches_site_default(sim):
    out = sim.baseline(n_sims=2000)
    assert len(out["table"]) == len(out["players"])
    assert abs(sum(r["TrophyPct"] for r in out["table"]) - 100) < 0.5
    assert abs(sum(r["JacketPct"] for r in out["table"]) - 100) < 0.5
    again = sim.baseline(n_sims=2000)
    assert again["table"] == out["table"]  # seeded: repeatable
    assert out["settings"]["method"] == "window"
    from teg_analysis.analysis.simulation import DEFAULT_SIMS
    assert sim.DEFAULT_N_SIMS == DEFAULT_SIMS and sim.baseline()["n_sims"] == DEFAULT_SIMS
    from teg_analysis.analysis import simulation as engine
    from teg_analysis.analysis.simulation import DEFAULT_RECENT_WEIGHTS
    assert list(out["settings"]["teg_weights"].values()) == list(DEFAULT_RECENT_WEIGHTS)
    assert out["settings"]["target"] == engine.default_target_teg()


def test_baseline_equals_default_prediction(sim):
    from webapp.routes.simulation import default_prediction
    site = default_prediction()
    out = sim.baseline()
    assert out["n_sims"] == site["simulations"] and out["teg"] == site["teg_num"]
    mine = {r["Player"]: r for r in out["table"]}
    for p in site["players"]:
        r = mine[p["Player"]]
        assert round(r["TrophyPct"], 1) == p["TrophyChancePct"]
        assert round(r["JacketPct"], 1) == p["JacketChancePct"]
        assert round(r["SpoonPct"], 1) == p["SpoonChancePct"]
        assert round(r["MeanStableford"], 1) == p["ExpectedStableford"]


def test_inputs_validated_like_site(sim):
    for kw in ({"weights": [50, -1]}, {"teg_weights": {18: float("nan")}}, {"shrinkage": -1},
               {"field_alpha": 500}, {"min_holes": 0}):
        with pytest.raises(sim.SimError):
            sim.whatif(n_sims=200, **kw)


def test_cli_and_api_round_handicaps_alike(sim):
    base = sim.baseline(n_sims=500)
    pl, hc = base["table"][0]["Pl"], base["table"][0]["Handicap"]
    api = sim.whatif(n_sims=500, handicaps={pl: hc + 2.6})
    args = sim._parser().parse_args(["whatif", "--handicap", f"{pl}={hc + 2.6}", "--n-sims", "500"])
    cli = sim.whatif(**sim._kwargs(args))
    assert api["table"] == cli["table"]


def test_whatif_handicap_and_history(sim):
    base = sim.baseline(n_sims=2000)
    pl = base["table"][0]["Pl"]
    hc = base["table"][0]["Handicap"]
    out = sim.whatif(n_sims=2000, handicaps={pl: hc + 4})
    row = next(r for r in out["table"] if r["Pl"] == pl)
    assert row["Handicap"] == hc + 4 and row["BaseHandicap"] == hc
    assert row["MeanStablefordDelta"] > 0 and row["TrophyDeltaPP"] > 0
    assert all(r["JacketDeltaPP"] == 0 for r in out["table"])  # strokes only
    ex = sim.whatif(n_sims=2000, exclude_tegs=[max(base["settings"]["teg_weights"])])
    assert max(ex["scenario_settings"]["teg_weights"]) < max(base["settings"]["teg_weights"])
    only = sim.whatif(n_sims=2000, only_tegs=[17, 18])
    assert set(only["scenario_settings"]["teg_weights"]) == {17, 18}


def test_whatif_accepts_names_and_rejects_unknown(sim):
    base = sim.baseline(n_sims=500)
    name = base["table"][0]["Player"]
    out = sim.whatif(n_sims=500, handicaps={name.lower(): base["table"][0]["Handicap"]})
    assert all(r["TrophyDeltaPP"] == 0 for r in out["table"])
    with pytest.raises(sim.SimError, match="not a known player"):
        sim.whatif(n_sims=500, handicaps={"Nobody Atall": 10})
    with pytest.raises(sim.SimError):
        sim.whatif(n_sims=500, teg_weights={999: 1})


def test_handicap_impact_and_equalising(sim):
    imp = sim.handicap_impact(n_sims=2000)
    assert imp["movers"]
    for r in imp["table"]:
        shares = sum(v for k, v in r.items() if k.startswith("from_"))
        assert abs(shares - r["TotalChangePP"]) < 0.05  # Shapley shares add up
    eq = sim.equalising(n_sims=2000)
    assert {"CurrentHC", "EqualisingHC", "Unrounded"} <= set(eq["table"][0])


def test_sim_cli_json_and_errors(extracted):
    script = str(SIM / "sim.py")
    env = {**os.environ, "TEG_ROOT": str(REPO)}
    ok = subprocess.run([sys.executable, script, "baseline", "--json", *SMALL],
                        capture_output=True, text=True, env=env)
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["table"]
    bad = subprocess.run([sys.executable, script, "whatif", "--handicap", "Zed=3", *SMALL],
                         capture_output=True, text=True, env=env)
    assert bad.returncode == 1 and bad.stderr.startswith("error:") and "Traceback" not in bad.stderr


# ---------------------------------------------------------------- tegstats

@pytest.fixture(scope="module")
def ts():
    os.environ["TEG_ROOT"] = str(REPO)
    sys.path.insert(0, str(STATS))
    import tegstats as mod
    yield mod
    sys.path.remove(str(STATS))


@pytest.fixture(scope="module")
def frames(ts):
    return ts.load_frames()


def test_frames_match_chatbot_datasets(frames):
    from teg_analysis.chatbot.tools import ChatData
    cd = ChatData()
    for mine, theirs in ((frames.rounds, cd.rounds()), (frames.tegs, cd.tegs())):
        pd.testing.assert_frame_equal(mine.reset_index(drop=True), theirs.reset_index(drop=True),
                                      check_dtype=False)


def test_winners_only_completed(frames):
    nums = frames.winners["TEG"].str.extract(r"(\d+)")[0].astype(int)
    assert set(nums) <= frames.complete


def test_rank_min_keeps_nan(ts):
    df = pd.DataFrame({"v": [3.0, np.nan, 3.0, 1.0]})
    assert ts.rank_min(df, "v").tolist() == [2, pd.NA, 2, 1]
    assert len(ts.top_n(df, "v", n=1)) == 2  # the two 3.0s tie; NaN is dropped


def test_rescore_keeps_hc_dtype(ts, frames):
    h = frames.holes.copy()
    h["HC"] = h["HC"].astype("int64")
    r = ts.rescore(h, delta={h["Pl"].iloc[0]: 2.4})
    assert r["HC"].dtype == h["HC"].dtype


def test_code_zip_only_py_and_skill_docs():
    for n in zipfile.ZipFile(io.BytesIO(tk.code_zip())).namelist():
        assert n.endswith((".py", ".md")), n
        if n.startswith("teg_analysis/"):
            assert n.endswith(".py")


def test_data_zip_cache_clears(monkeypatch):
    a = tk.data_zip()
    assert tk.data_zip() is a
    tk.clear_data_cache()
    assert tk.data_zip() is not a


def test_net_measure_by_era(ts):
    assert ts.net_measure(7) == "NetVP" and ts.net_measure(8) == "Stableford"
    assert ts.STABLEFORD_ERA_TEG == 8
    df = pd.DataFrame({"TEGNum": [7, 8], "NetVP": [3, 4], "Stableford": [30, 31]})
    assert ts.net_score(df).tolist() == [3, 31]


def test_ties_rank_and_top_n(ts):
    df = pd.DataFrame({"v": [10, 9, 9, 9, 5]})
    assert ts.rank_min(df, "v", ascending=False).tolist() == [1, 2, 2, 2, 5]
    assert len(ts.top_n(df, "v", n=2)) == 4  # all three tied at 2nd are kept


def test_positions_agree_with_winners(frames):
    t = frames.tegs[frames.tegs.Complete & (frames.tegs.TEGNum >= 8)]
    winners = t[t.TrophyPosition == 1].groupby("TEGNum")["Player"].apply(set)
    official = frames.winners.set_index("TEG")["TEG Trophy"]
    for teg, names in winners.items():
        off = str(official.get(f"TEG {teg}", "")).rstrip("*")
        if off:
            assert off in names


def test_rescore_reproduces_recorded_stableford(ts, frames):
    h = frames.holes
    r = ts.rescore(h)
    assert (r["Stableford"] == h["Stableford"]).all()
    assert (r["HCStrokes"] == h["HCStrokes"]).all()
    sample = h.sample(300, random_state=1)
    expect = (2 - (sample.GrossVP - ts.strokes_received(sample.HC.astype(int), sample.SI))).clip(lower=0)
    assert (expect == sample.Stableford).all()


def test_rescore_counterfactual(ts, frames):
    h = frames.holes
    pl = h["Pl"].iloc[0]
    teg = int(h[h.Pl == pl]["TEGNum"].iloc[-1])
    r = ts.rescore(h, delta={pl: 4}, teg=teg)
    m = (r.Pl == pl) & (r.TEGNum == teg)
    assert (r.loc[m, "Stableford"] >= h.loc[m, "Stableford"]).all()
    assert r.loc[m, "Stableford"].sum() > h.loc[m, "Stableford"].sum()
    assert (r.loc[~m, "Stableford"] == h.loc[~m, "Stableford"]).all()
    assert (r["GrossVP"] == h["GrossVP"]).all()
    with pytest.raises(ValueError):
        ts.rescore(h, handicaps={"ZZ": 1})


def test_bootstrap_shapes(ts):
    x = np.random.default_rng(0).normal(5, 2, 200)
    ci = ts.bootstrap_ci(x, n_boot=500)
    assert ci["lo"] < ci["est"] < ci["hi"] and ci["n"] == 200 and not ci["small_n"]
    d = ts.bootstrap_diff_ci(x + 1, x, n_boot=500)
    assert d["excludes_zero"] and abs(d["diff"] - 1) < 1e-9
    assert ts.bootstrap_ci([1, 2, 3])["small_n"] and ts.small_sample(5)


def test_vs_own_baseline(ts, frames):
    h = frames.holes
    out = ts.vs_own_baseline(h, "GrossVP", h["Hole"] == 18, n_boot=200)
    assert out.iloc[-1]["Pl"] == "ALL"
    assert {"n_in", "n_out", "diff", "lo", "hi", "small_n"} <= set(out.columns)
    assert out.iloc[-1]["n_in"] == (h["Hole"] == 18).sum()
    assert out["lo"].le(out["diff"]).all() and out["diff"].le(out["hi"]).all()


def test_describe_data_prints(ts, frames, capsys):
    ts.describe_data(frames)
    out = capsys.readouterr().out
    assert "holes:" in out and "net competition" in out


# ---------------------------------------------------------------- precomputed tables

def test_data_zip_has_precomputed_tables():
    names = set(zipfile.ZipFile(io.BytesIO(tk.data_zip())).namelist())
    for n in tk.PRECOMPUTED:
        if (REPO / "data" / f"{n}.parquet").exists():
            assert f"data/{n}.parquet" in names
    assert "streaks" in tk.PRECOMPUTED and len(tk.PRECOMPUTED) == 7


def test_load_precomputed(ts):
    assert set(tk.PRECOMPUTED) <= set(ts.load_precomputed()) | {
        n for n in tk.PRECOMPUTED if not (REPO / "data" / f"{n}.parquet").exists()}
    df = ts.load_precomputed("bestball")
    assert len(df) and "Format" in df.columns
    with pytest.raises(ValueError, match="Available:.*streaks"):
        ts.load_precomputed("nope")


def test_precomputed_doc_covers_every_table():
    doc = (REPO / "teg_analysis/chatbot/toolkit/skills/teg-analysis/reference/precomputed.md").read_text()
    for n in tk.PRECOMPUTED:
        assert n in doc, n
