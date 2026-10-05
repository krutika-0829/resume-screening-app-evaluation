"""
Threshold calibration -- run this against your live app (with the debug-enabled
main.py) to see the actual gap between "genuinely relevant" and "genuinely nothing"
queries, so SIMILARITY_THRESHOLD can be set from real data instead of a guess.

Usage:
    python calibrate_threshold.py
"""

import requests
import time

API_URL = "http://127.0.0.1:8000/query"


known_good = [
    "Python developer with FastAPI experience",
    "Data scientist with machine learning experience",
    "Candidates with AWS certification",
]


known_negative = [
    "Candidates with blockchain or smart contract development experience",
    "Candidates with a pilot's license or aviation experience",
    "Candidates with quantum computing research experience",
]


def get_distance(query_text):
    response = requests.post(API_URL, json={"query": query_text}, timeout=60)
    response.raise_for_status()
    data = response.json()
    if "_debug_best_distance" not in data:
        print(f"\n  MISSING _debug_best_distance in response for query: {query_text!r}")
        print(f"  Full response was: {data}\n")
        return None
    return data["_debug_best_distance"]


def main():
    print("=" * 70)
    print("KNOWN-GOOD queries (should have LOW distance -- real matches exist)")
    print("=" * 70)
    good_distances = []
    for q in known_good:
        d = get_distance(q)
        good_distances.append(d)
        if d is not None:
            print(f"  {d:.4f}   {q}")
        else:
            print(f"  [NO VALUE]   {q}")
        time.sleep(2)

    print()
    print("=" * 70)
    print("KNOWN-NEGATIVE queries (should have HIGH distance -- nothing matches)")
    print("=" * 70)
    bad_distances = []
    for q in known_negative:
        d = get_distance(q)
        bad_distances.append(d)
        if d is not None:
            print(f"  {d:.4f}   {q}")
        else:
            print(f"  [NO VALUE]   {q}")
        time.sleep(2)

    print()
    print("=" * 70)
    print("SUGGESTED THRESHOLD")
    print("=" * 70)
    good_clean = [d for d in good_distances if d is not None]
    bad_clean = [d for d in bad_distances if d is not None]

    if len(good_clean) < len(good_distances) or len(bad_clean) < len(bad_distances):
        print("Some queries returned no distance value -- see 'MISSING' messages above.")
        print("This almost always means the server is running old code (not restarted")
        print("after the main.py patch) or main.py wasn't saved correctly. Fix that first,")
        print("then rerun this script -- the numbers below only reflect the queries that worked.\n")

    if good_clean and bad_clean:
        max_good = max(good_clean)
        min_bad = min(bad_clean)
        print(f"Highest distance among known-good queries: {max_good:.4f}")
        print(f"Lowest distance among known-negative queries: {min_bad:.4f}")
        if max_good < min_bad:
            suggested = (max_good + min_bad) / 2
            print(f"\nClear gap found. Suggested SIMILARITY_THRESHOLD ~= {suggested:.4f}")
        else:
            print("\nWARNING: good and negative distances OVERLAP -- there's no clean cutoff.")
            print("This means a single distance threshold can't cleanly separate real matches")
            print("from nonsense queries for your embedding model. Consider a different signal")
            print("(e.g. score gap between top-1 and top-5, or a small classifier) instead.")
    else:
        print("Not enough valid data to suggest a threshold -- fix the MISSING responses first.")


if __name__ == "__main__":
    main()