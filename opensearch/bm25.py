"""
Standalone BM25 keyword search against OpenSearch.

Usage:
    python bm25_opensearch_search.py
(prompts for a query, prints results)

Or import search() directly to use it elsewhere without running this file.
"""

from opensearch.client import get_client, INDEX_NAME
from llm import query_parser
from langchain_core.documents import Document


def search(query, user_id=None, k=10):
    """
    Runs a BM25 match query against chunk_text (scored using the
    resume_analyzer set up in setup_opensearch_index.py -- lowercased,
    stopwords removed, stemmed). Optionally scoped to one user_id.

    Returns a list of dicts: {score, source, candidate_name, chunk_index, chunk_text}
    """
    query = query_parser(query)
    print("parsed query :", query ) # Use the query parser to rewrite the query for BM25 search
    client = get_client()

    must_clauses = {"match": {"chunk_text": {"query": query}}}
    filter_clauses = []
    if user_id is not None:
        filter_clauses.append({"term": {"user_id": user_id}})

    body = {
        "size": k,
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
            }
        }
    }

    response = client.search(index=INDEX_NAME, body=body)

    results = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        doc = Document(
            page_content=source["chunk_text"],
            metadata={
                "source": source["source"],
                "candidate_name": source["candidate_name"],
               
            }
        )

        results.append(doc)
    return results


# if __name__ == "__main__":

#     while True : 
#         print("After using query parser")
#         query = input("Enter a query: ").strip()
#         user_id = input("Filter by user_id (leave blank for all): ").strip() or None

#         if query == "exit":
#             break

#         results = search(query, user_id=user_id, k=10)
#         print(results)

        # print(f"\n{len(results)} results:\n")
        # for i, r in enumerate(results, start=1):
        #     snippet = r["chunk_text"][:150].replace("\n", " ")
        #     print(f"{i}. [{r['candidate_name']} | {r['source']}] score={r['score']:.4f}")
        #     print(f"   {snippet}...\n")











#   results = []
#     for hit in response["hits"]["hits"]:
#         source = hit["_source"]
#         results.append({
#             "score": hit["_score"],
#             "source": source["source"],
#             "candidate_name": source["candidate_name"],
#             "chunk_index": source["chunk_index"],
#             "chunk_text": source["chunk_text"],
#         })
#     return results