import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "golden_set.jsonl"
SUMMARY_FILE = ROOT / "reports" / "summary.json"
RESULTS_FILE = ROOT / "reports" / "benchmark_results.json"
FAILURE_FILE = ROOT / "analysis" / "failure_analysis.md"
REFLECTIONS_DIR = ROOT / "analysis" / "reflections"
RUN_LOG = ROOT / "reports" / "dashboard_last_run.log"

st.set_page_config(page_title="AI Eval Factory Dashboard", layout="wide")


# =========================
# Utils
# =========================
def read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def run_shell_command(command: str) -> str:
    proc = subprocess.run(
        command,
        cwd=str(ROOT),
        shell=True,
        text=True,
        capture_output=True,
    )
    output = []
    output.append(f"$ {command}")
    output.append(proc.stdout.strip())
    if proc.stderr.strip():
        output.append("[stderr]")
        output.append(proc.stderr.strip())
    output.append(f"[exit_code] {proc.returncode}")
    return "\n".join(x for x in output if x)


def save_run_log(content: str) -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(RUN_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n\n=== {datetime.now().isoformat(timespec='seconds')} ===\n")
        f.write(content)


# =========================
# Logic
# =========================
def checklist_progress(dataset: List[Dict], summary: Dict, results: List[Dict]) -> pd.DataFrame:
    metrics = summary.get("metrics", {}) if summary else {}
    regression = summary.get("regression", {}) if summary else {}

    dataset_ok = len(dataset) >= 50 and all(
        "question" in x and "expected_answer" in x and "expected_retrieval_ids" in x for x in dataset
    )
    retrieval_ok = "hit_rate" in metrics and "avg_mrr" in metrics
    judge_ok = "agreement_rate" in metrics and any(r.get("judge", {}).get("using_openai") for r in results)
    regression_ok = bool(regression)

    failure_ok = FAILURE_FILE.exists() and "X/Y" not in FAILURE_FILE.read_text(encoding="utf-8")
    reflection_files = sorted(REFLECTIONS_DIR.glob("reflection_*.md")) if REFLECTIONS_DIR.exists() else []
    reflections_ok = len(reflection_files) >= 6

    items = [
        ("Golden dataset ready", dataset_ok),
        ("Retrieval metrics ready", retrieval_ok),
        ("Multi-judge AI ready", judge_ok),
        ("Regression gate ready", regression_ok),
        ("Failure report completed", failure_ok),
        ("6 reflections completed", reflections_ok),
    ]

    return pd.DataFrame(items, columns=["task", "done"])


def build_results_dataframe(results: List[Dict]) -> pd.DataFrame:
    rows = []
    for row in results:
        rows.append(
            {
                "test_case": row.get("test_case", ""),
                "status": row.get("status", ""),
                "score": row.get("judge", {}).get("final_score", 0.0),
                "agreement": row.get("judge", {}).get("agreement_rate", 0.0),
                "faithfulness": row.get("ragas", {}).get("faithfulness", 0.0),
                "relevancy": row.get("ragas", {}).get("relevancy", 0.0),
                "hit_rate": row.get("ragas", {}).get("retrieval", {}).get("hit_rate", 0.0),
                "mrr": row.get("ragas", {}).get("retrieval", {}).get("mrr", 0.0),
                "latency": row.get("latency", 0.0),
                "token_usage": row.get("token_usage", 0),
                "cost_usd": row.get("estimated_cost_usd", 0.0),
                "using_openai": row.get("judge", {}).get("using_openai", False),
            }
        )
    return pd.DataFrame(rows)


# =========================
# UI
# =========================
st.title("AI Evaluation Factory Dashboard")
st.caption("Run pipeline, inspect logs, monitor completion, and review benchmark charts.")

left, right = st.columns([1, 2])

# =========================
# LEFT PANEL
# =========================
with left:
    st.subheader("Run Commands")

    if st.button("Run: synthetic_gen"):
        with st.spinner("Running synthetic_gen..."):
            out = run_shell_command(f'"{sys.executable}" data/synthetic_gen.py')
            save_run_log(out)
            st.session_state["last_cmd"] = out

    if st.button("Run: benchmark main"):
        with st.spinner("Running main benchmark..."):
            out = run_shell_command(f'"{sys.executable}" main.py')
            save_run_log(out)
            st.session_state["last_cmd"] = out

    if st.button("Run: check_lab"):
        with st.spinner("Running check_lab..."):
            out = run_shell_command(f'"{sys.executable}" check_lab.py')
            save_run_log(out)
            st.session_state["last_cmd"] = out

    if st.button("Run Full Pipeline"):
        full_log = []
        for cmd in [
            f'"{sys.executable}" data/synthetic_gen.py',
            f'"{sys.executable}" main.py',
            f'"{sys.executable}" check_lab.py',
        ]:
            with st.spinner(f"Running {cmd}..."):
                step_log = run_shell_command(cmd)
                full_log.append(step_log)

        merged = "\n\n".join(full_log)
        save_run_log(merged)
        st.session_state["last_cmd"] = merged

    st.subheader("Latest Log")
    st.code(st.session_state.get("last_cmd", "No command run yet."), language="text")

    if RUN_LOG.exists():
        with st.expander("Run History Log"):
            st.code(RUN_LOG.read_text(encoding="utf-8"), language="text")


# =========================
# RIGHT PANEL
# =========================
with right:
    dataset = read_jsonl(DATA_FILE)
    summary = read_json(SUMMARY_FILE)
    results = read_json(RESULTS_FILE)

    df_check = checklist_progress(dataset, summary, results)

    done_count = int(df_check["done"].sum())
    total_count = len(df_check)
    pct = int((done_count / total_count) * 100) if total_count else 0

    st.subheader("Completion")
    st.progress(pct / 100)
    st.write(f"{pct}% complete ({done_count}/{total_count} tasks)")
    st.dataframe(df_check, width="stretch")

    # =========================
    # Metrics
    # =========================
    metrics = summary.get("metrics", {}) if summary else {}
    meta = summary.get("metadata", {}) if summary else {}

    st.subheader("Key Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total cases", int(meta.get("total", 0)))
    c2.metric("Avg score", f"{metrics.get('avg_score', 0):.3f}")
    c3.metric("Hit Rate", f"{metrics.get('hit_rate', 0)*100:.1f}%")
    c4.metric("Agreement", f"{metrics.get('agreement_rate', 0)*100:.1f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Pass Rate", f"{metrics.get('pass_rate', 0)*100:.1f}%")
    c6.metric("Avg MRR", f"{metrics.get('avg_mrr', 0):.3f}")
    c7.metric("Avg latency (s)", f"{metrics.get('avg_latency_sec', 0):.3f}")
    c8.metric("Cost/eval (USD)", f"{metrics.get('cost_per_eval_usd', 0):.6f}")

    # =========================
    # Charts
    # =========================
    if results:
        st.subheader("Charts")
        dfr = build_results_dataframe(results)

        st.write("Score distribution")
        st.bar_chart(dfr["score"].value_counts().sort_index())

        st.write("Pass vs Fail")
        st.bar_chart(dfr["status"].value_counts())

        st.write("Latency by case index")
        latency_df = dfr[["latency"]].copy()
        latency_df.index = range(1, len(latency_df) + 1)
        st.line_chart(latency_df)

        st.write("Worst 10 cases by relevancy")
        worst = dfr.sort_values("relevancy").head(10)
        st.dataframe(
            worst[["test_case", "status", "relevancy", "faithfulness", "score", "agreement"]],
            width="stretch",
        )

        st.write("Hard-case category coverage")
        cat_rows = [x.get("metadata", {}).get("hard_case_category", "base") for x in dataset]
        cat_df = pd.Series(cat_rows).value_counts()
        st.bar_chart(cat_df)

    # =========================
    # Files
    # =========================
    st.subheader("Report Files")
    st.write(f"summary.json: {'OK' if SUMMARY_FILE.exists() else 'Missing'}")
    st.write(f"benchmark_results.json: {'OK' if RESULTS_FILE.exists() else 'Missing'}")
    st.write(f"failure_analysis.md: {'OK' if FAILURE_FILE.exists() else 'Missing'}")
    st.write(
        f"reflections count: {len(list(REFLECTIONS_DIR.glob('reflection_*.md')) if REFLECTIONS_DIR.exists() else [])}"
    )