import json
from collections import Counter

with open("reports/benchmark_results.json", "r", encoding="utf-8") as f:
    results = json.load(f)

total = len(results)
pass_count = sum(1 for r in results if r["status"] == "pass")
fail_count = total - pass_count

type_counts = Counter()
type_pass = Counter()
type_fail = Counter()
retrieval_miss = 0

for r in results:
    ct = r["metadata"]["case_type"]
    type_counts[ct] += 1
    if r["status"] == "pass":
        type_pass[ct] += 1
    else:
        type_fail[ct] += 1
    if r["ragas"]["retrieval"]["hit_rate"] == 0:
        retrieval_miss += 1

print("Total:", total)
print("Pass:", pass_count, "Fail:", fail_count)
print("Pass rate: {:.2f}%".format(pass_count/total*100))
print()
print("By case_type:")
for ct in sorted(type_counts.keys()):
    print("  {}: total={}, pass={}, fail={}".format(ct, type_counts[ct], type_pass[ct], type_fail[ct]))
print("Retrieval miss (hit_rate=0):", retrieval_miss)

# Find worst cases
worst = sorted(results, key=lambda r: r["judge"]["final_score"])
print()
print("=== 5 worst cases ===")
for i, r in enumerate(worst[:5]):
    ct = r["metadata"]["case_type"]
    score = r["judge"]["final_score"]
    hr = r["ragas"]["retrieval"]["hit_rate"]
    faith = r["ragas"]["faithfulness"]
    rel = r["ragas"]["relevancy"]
    print("Case {}: type={}, score={}, hit_rate={}, faith={}, rel={}".format(i+1, ct, score, hr, faith, rel))
    print("  Q:", r["test_case"][:100])
    print("  Expected:", r["expected_answer"][:100])
    print("  Agent:", r["agent_response"][:100])
    print()

# Metrics averages
avg_score = sum(r["judge"]["final_score"] for r in results) / total
hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
mrr = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total
agreement_rate = sum(r["judge"]["agreement_rate"] for r in results) / total
avg_faithfulness = sum(r["ragas"]["faithfulness"] for r in results) / total
avg_relevancy = sum(r["ragas"]["relevancy"] for r in results) / total
avg_latency = sum(r["latency"] for r in results) / total
avg_tokens = sum(r["metadata"]["agent"].get("tokens_used", 0) for r in results) / total

print("Avg score:", round(avg_score, 4))
print("Hit rate:", round(hit_rate, 4))
print("MRR:", round(mrr, 4))
print("Agreement rate:", round(agreement_rate, 4))
print("Faithfulness:", round(avg_faithfulness, 4))
print("Relevancy:", round(avg_relevancy, 4))
print("Avg latency:", round(avg_latency, 4))
print("Avg tokens:", round(avg_tokens, 2))

# Position bias stats
biased = sum(1 for r in results if r["judge"].get("position_bias", {}).get("is_biased", False))
print("Position bias cases: {}/{}".format(biased, total))

# Conflict resolutions
conflict_counts = Counter(r["judge"].get("conflict_resolution", "unknown") for r in results)
print("Conflict resolutions:", dict(conflict_counts))

# Scoring modes
mode_counts = Counter(r["judge"].get("scoring_mode", "unknown") for r in results)
print("Scoring modes:", dict(mode_counts))

# Per category
for ct in ["standard", "edge", "adversarial"]:
    ct_results = [r for r in results if r["metadata"]["case_type"] == ct]
    ct_pass = [r for r in ct_results if r["status"] == "pass"]
    ct_fail = [r for r in ct_results if r["status"] == "fail"]
    ct_miss = sum(1 for r in ct_results if r["ragas"]["retrieval"]["hit_rate"] == 0)
    ct_avg_score = sum(r["judge"]["final_score"] for r in ct_results) / max(len(ct_results), 1)
    ct_avg_faith = sum(r["ragas"]["faithfulness"] for r in ct_results) / max(len(ct_results), 1)
    print("\n{}: total={}, pass={}, fail={}, retrieval_miss={}, avg_score={:.2f}, avg_faith={:.4f}".format(
        ct, len(ct_results), len(ct_pass), len(ct_fail), ct_miss, ct_avg_score, ct_avg_faith))

# Specific pattern analysis
print("\n=== PASS cases detail ===")
for r in results:
    if r["status"] == "pass":
        ct = r["metadata"]["case_type"]
        score = r["judge"]["final_score"]
        hr = r["ragas"]["retrieval"]["hit_rate"]
        print("PASS: type={}, score={}, hit_rate={}, Q={}".format(ct, score, hr, r["test_case"][:80]))
