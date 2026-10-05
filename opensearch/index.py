"""
Run once to create the "resume_chunks" index:
    python setup_opensearch_index.py

Uses a custom analyzer (lowercase + English stopwords + English stemming)
instead of OpenSearch's plain default -- this is the lever that actually
moves relevance the most (more than any similarity/BM25 parameter tuning),
same finding as when we tuned your standalone rank_bm25 script earlier.

OpenSearch's default similarity IS BM25 already (BM25(k1=1.2, b=0.75)) --
you don't need to configure anything extra to "turn on" BM25, it's the
default scoring model. What you're tuning here is the *analyzer* (how text
gets broken into terms before BM25 ever runs on it), which matters more.
"""

from client import get_client, INDEX_NAME

client = get_client()

index_body = {
    "settings": {
        "analysis": {
            "filter": {
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_stop": {
                    "type": "stop",
                    "stopwords": "_english_"
                }
            },
            "analyzer": {
                "resume_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "english_stop", "english_stemmer"]
                }
            }
        }
        # If you want to tune BM25's own k1/b directly (separate from the
        # analyzer above), you'd add a custom "similarity" block here, e.g.:
        # "similarity": {
        #     "resume_bm25": {"type": "BM25", "k1": 1.5, "b": 0.75}
        # }
        # ...then reference "similarity": "resume_bm25" on chunk_text below.
        # Left at OpenSearch's default for now -- tune only if the analyzer
        # change alone isn't enough.
    },
    "mappings": {
        "properties": {
            "user_id": {"type": "keyword"},
            "source": {"type": "keyword"},          # resume filename
            "candidate_name": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "chunk_text": {
                "type": "text",
                "analyzer": "resume_analyzer"
            }
        }
    }
}

if __name__ == "__main__":
    if client.indices.exists(index=INDEX_NAME):
        
        print(f"Index '{INDEX_NAME}' already exists -- doing nothing. "
              f"Delete it first (client.indices.delete(index='{INDEX_NAME}')) if you want to recreate it.")
    else:
        client.indices.create(index=INDEX_NAME, body=index_body)
        print(f"Created index '{INDEX_NAME}'.")