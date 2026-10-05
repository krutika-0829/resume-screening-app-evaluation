"""
Automated retrieval capture for Stage 1 evaluation -- wired to YOUR actual
resume screening app's /query endpoint (api.py + patched main.py).

Requires: main.py to be patched with retrieved_sources / final_sources
(see main_patched.py) so the API response actually contains ranked source lists.

Usage:
    python run_retrieval_capture.py
"""

import json
import time
import requests
 
API_URL = "http://127.0.0.1:8000/query"   # change host/port if different
REQUEST_TIMEOUT = 120                      # Groq calls can be slow, especially at rate limits
DELAY_BETWEEN_CALLS = 2.0                  # seconds -- protects your Groq daily token budget
 
 
def call_query_endpoint(query_text: str) -> dict:
    response = requests.post(
        API_URL,
        json={"query": query_text},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
 
 
def run_single_query(query_text: str):
    """Returns (retrieved_before_filter, final_after_filter) as ranked source lists."""
    api_response = call_query_endpoint(query_text)
    retrieved = api_response.get("retrieved_sources", [])
    final = api_response.get("final_sources", [])
    return retrieved, final
 
 
def run_comparison_query(sides: dict):
    """
    Comparison queries (e.g. React vs Angular) need one API call per side.
    Returns (before_dict, after_dict) keyed by side.
    """
    before_result = {}
    after_result = {}
    for side_key in sides.keys():
        side_query = f"Candidates with {side_key} experience"
        retrieved, final = run_single_query(side_query)
        before_result[side_key] = retrieved
        after_result[side_key] = final
        time.sleep(DELAY_BETWEEN_CALLS)
    return before_result, after_result
 
 
def main():
    golden = json.load(open("golden_dataset.json"))
    output = {"results": {}}
 
    total = len(golden["golden_set"])
    for i, item in enumerate(golden["golden_set"], start=1):
        query_text = item["query"]
        # No "category" field anymore -- detect comparison queries by shape instead:
        # comparison queries store relevant_resumes as a dict ({"react": [...], "angular": [...]}),
        # normal queries store it as a plain list.
        is_comparison = isinstance(item["relevant_resumes"], dict)
        print(f"[{i}/{total}] Running: {query_text}")
 
        try:
            if is_comparison:
                before, after = run_comparison_query(item["relevant_resumes"])
                output["results"][query_text] = {
                    "retrieved_before_filter": before,
                    "final_after_filter": after,
                }
            else:
                retrieved, final = run_single_query(query_text)
                output["results"][query_text] = {
                    "retrieved_before_filter": retrieved,
                    "final_after_filter": final,
                }
                print(f"    retrieved: {retrieved}")
                print(f"    final:     {final}")
 
        except requests.exceptions.RequestException as e:
            print(f"    REQUEST ERROR: {e}")
            output["results"][query_text] = _empty_result(item, is_comparison)
 
        except Exception as e:
            print(f"    ERROR: {e}")
            output["results"][query_text] = _empty_result(item, is_comparison)
 
        time.sleep(DELAY_BETWEEN_CALLS)
 
    with open("retrieval_results.json", "w") as f:
        json.dump(output, f, indent=2)
 
    print(f"\nDone. Wrote retrieval_results.json with {len(output['results'])} query results.")
    print("Next step: python evaluate_retrieval.py")
 
 
def _empty_result(item, is_comparison):
    if is_comparison:
        keys = list(item["relevant_resumes"].keys())
        return {
            "retrieved_before_filter": {k: [] for k in keys},
            "final_after_filter": {k: [] for k in keys},
        }
    return {"retrieved_before_filter": [], "final_after_filter": []}
 
 
if __name__ == "__main__":
    main()