"""
Stage 1 Retrieval Evaluation for Resume Screening App
Computes Precision@k, Recall@k, Hit Rate, MRR, nDCG@k
Compares 'before metadata filtering' vs 'after metadata filtering'

Usage:
    python evaluate_retrieval.py

Requires:
    golden_dataset.json          (query -> relevant resume IDs, ground truth)
    retrieval_results.json       (query -> your app's actual retrieved IDs, both stages)
"""

import json
import math
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()
import os
from groq import Groq
 
K = 15
 
 
def normalize_id(resume_id: str) -> str:
    """
    Makes matching robust to filename mismatches: strips file extension,
    lowercases, and strips whitespace. So 'resume_1', 'resume_1.pdf', and
    'RESUME_1.PDF' all compare equal.
    """
    if not resume_id:
        return resume_id
    resume_id = resume_id.strip().lower()
    if "." in resume_id:
        resume_id = resume_id.rsplit(".", 1)[0]
    return resume_id
 
 
def normalize_list(ids):
    return [normalize_id(i) for i in ids]
 
 
def normalize_set(ids):
    return {normalize_id(i) for i in ids}
 
 
def precision_at_k(retrieved, relevant, k):
    if not retrieved:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(top_k)
 
 
def recall_at_k(retrieved, relevant, k):
    if not relevant:
        return None  
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(relevant)
 
 
def hit_rate_at_k(retrieved, relevant, k):
    if not relevant:
        return None
    top_k = retrieved[:k]
    return 1.0 if any(r in relevant for r in top_k) else 0.0
 
 
def reciprocal_rank(retrieved, relevant):
    if not relevant:
        return None
    for i, r in enumerate(retrieved, start=1):
        if r in relevant:
            return 1.0 / i
    return 0.0
 
 
def ndcg_at_k(retrieved, relevant, k):
    if not relevant:
        return None
    top_k = retrieved[:k]
    dcg = sum(1.0 / math.log2(i + 1) for i, r in enumerate(top_k, start=1) if r in relevant)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    if idcg == 0:
        return None
    return dcg / idcg
 
 
def evaluate_single(retrieved, relevant, k):
    return {
        "precision@k": precision_at_k(retrieved, relevant, k),
        "recall@k": recall_at_k(retrieved, relevant, k),
        "hit_rate@k": hit_rate_at_k(retrieved, relevant, k),
        "mrr": reciprocal_rank(retrieved, relevant),
        "ndcg@k": ndcg_at_k(retrieved, relevant, k),
    }
 
 
def safe_avg(values):
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)
 
 
def main():
    golden = json.load(open("golden_dataset.json"))
    results = json.load(open("retrieval_results.json"))["results"]
 
    stages = ["retrieved_before_filter", "final_after_filter"]
    per_stage_scores = {stage: defaultdict(list) for stage in stages}
 
    print(f"\n{'='*90}")
    print(f"STAGE 1 RETRIEVAL EVALUATION (k={K})")
    print(f"{'='*90}\n")
 
    for item in golden["golden_set"]:
        query = item["query"]
        # No "category" field anymore -- detect comparison queries by shape instead:
        # comparison queries store relevant_resumes as a dict, normal queries as a list.
        is_comparison = isinstance(item["relevant_resumes"], dict)
 
        if query not in results:
            print(f"[SKIPPED - no results logged] {query}")
            continue
 
        if is_comparison:
            # relevant_resumes and results are both dicts keyed by side (e.g. "react"/"angular")
            for side, relevant in item["relevant_resumes"].items():
                relevant_norm = normalize_set(relevant)
                for stage in stages:
                    retrieved = results[query][stage].get(side, [])
                    retrieved_norm = normalize_list(retrieved)
                    scores = evaluate_single(retrieved_norm, relevant_norm, K)
                    for metric, val in scores.items():
                        if val is not None:
                            per_stage_scores[stage][metric].append(val)
                    print(f"[comparison] {query} :: side={side} :: stage={stage}")
                    print(f"    relevant={relevant}")
                    print(f"    retrieved_top{K}={retrieved[:K]}")
                    print(f"    scores={ {k: round(v,3) if v is not None else None for k,v in scores.items()} }\n")
        else:
            relevant = set(item["relevant_resumes"])
            relevant_norm = normalize_set(relevant)
            for stage in stages:
                retrieved = results[query][stage]
                retrieved_norm = normalize_list(retrieved)
                scores = evaluate_single(retrieved_norm, relevant_norm, K)
                for metric, val in scores.items():
                    if val is not None:
                        per_stage_scores[stage][metric].append(val)
                print(f"{query} :: stage={stage}")
                print(f"    relevant={sorted(relevant) if relevant else '(none - negative query)'}")
                print(f"    retrieved_top{K}={retrieved[:K]}")
                print(f"    scores={ {k: round(v,3) if v is not None else None for k,v in scores.items()} }\n")
 
    # Summary table
    print(f"\n{'='*90}")
    print("SUMMARY (averaged across all queries where metric is defined)")
    print(f"{'='*90}")
    print(f"{'Metric':<15} {'Before Filter':<20} {'After Filter':<20} {'Delta':<10}")
    print("-" * 65)
 
    metrics = ["precision@k", "recall@k", "hit_rate@k", "mrr", "ndcg@k"]
    for metric in metrics:
        before = safe_avg(per_stage_scores["retrieved_before_filter"][metric])
        after = safe_avg(per_stage_scores["final_after_filter"][metric])
        before_str = f"{before:.3f}" if before is not None else "N/A"
        after_str = f"{after:.3f}" if after is not None else "N/A"
        delta_str = f"{(after - before):+.3f}" if (before is not None and after is not None) else "N/A"
        print(f"{metric:<15} {before_str:<20} {after_str:<20} {delta_str:<10}")
 
    print(f"\n{'='*90}")
    print("Negative queries (empty relevant set) are excluded from precision/recall/MRR/nDCG averages")
    print("since those metrics are undefined with zero relevant items -- check the per-query log above")
    print("to see if your system correctly returned nothing/low-confidence for those.")
    print(f"{'='*90}\n")
 
 
if __name__ == "__main__":
    main()