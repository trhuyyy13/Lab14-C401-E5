import json
import os

def validate_lab():
    print("[INFO] Validating lab submission format...")

    required_files = [
        "reports/summary.json",
        "reports/benchmark_results.json",
        "analysis/failure_analysis.md"
    ]

    # 1. Kiểm tra sự tồn tại của tất cả file
    missing = []
    for f in required_files:
        if os.path.exists(f):
            print(f"FOUND: {f}")
        else:
            print(f"MISSING: {f}")
            missing.append(f)

    if missing:
        print(f"\n[ERROR] Missing {len(missing)} file(s). Please add them before submitting.")
        return

    # 2. Kiểm tra nội dung summary.json
    try:
        with open("reports/summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] reports/summary.json is not a valid JSON: {e}")
        return

    if "metrics" not in data or "metadata" not in data:
        print("[ERROR] summary.json is missing 'metrics' or 'metadata'.")
        return

    metrics = data["metrics"]

    print(f"\n--- Quick Stats ---")
    print(f"Total cases: {data['metadata'].get('total', 'N/A')}")
    print(f"Average score: {metrics.get('avg_score', 0):.2f}")

    # EXPERT CHECKS
    has_retrieval = "hit_rate" in metrics
    if has_retrieval:
        print(f"OK: Found Retrieval Metrics (Hit Rate: {metrics['hit_rate']*100:.1f}%)")
    else:
        print(f"WARNING: Missing Retrieval Metrics (hit_rate).")

    has_multi_judge = "agreement_rate" in metrics
    if has_multi_judge:
        print(f"OK: Found Multi-Judge Metrics (Agreement Rate: {metrics['agreement_rate']*100:.1f}%)")
    else:
        print(f"WARNING: Missing Multi-Judge Metrics (agreement_rate).")

    if data["metadata"].get("version"):
        print(f"OK: Found Agent version info (Regression Mode)")

    print("\n[SUCCESS] Lab is ready for grading!")

if __name__ == "__main__":
    validate_lab()
