import numpy as np
import faiss
from sentence_transformers import CrossEncoder
import torch




# Loaded once at import time, same pattern as your existing SentenceTransformer model.
# ~80MB, runs fine on CPU for small batches (we only re-rank ~15 chunks per query).
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2",activation_fn=torch.nn.Sigmoid())

def create_faiss_index(model, chunks):
    texts = [chunk.page_content for chunk in chunks]

    embeddings = model.encode(texts)
    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]

    
    
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index


def cap_per_document(ranked_chunks, k=10, max_per_doc=2):
    """
    it avoids retrival of multiple chunks from same resume
    """
    counts = {}
    result = []
    for chunk in ranked_chunks:  # already sorted by score desc
        source = chunk.metadata.get("source")
        if counts.get(source, 0) < max_per_doc:
            result.append(chunk)
            counts[source] = counts.get(source, 0) + 1
        if len(result) == k:
            break
    return result




def retrieve_chunks(query, model, index, chunks, k):
    query_embedding = model.encode(query)
    query_embedding = np.array([query_embedding]).astype("float32")

    distances, indices = index.search(query_embedding, k)

    retrieved_chunks = [chunks[i] for i in indices[0]]


    

    return retrieved_chunks






def rerank_chunks(query, chunks):
    """
    Re-scores an already-retrieved list of chunks using a cross-encoder,
    which looks at (query, chunk) pairs jointly instead of comparing separate
    embeddings -- generally much better at judging true relevance than the
    bi-encoder FAISS search alone. Returns chunks re-sorted best-first.
 
    No API calls involved -- runs entirely locally.
    """
    if not chunks:
        return chunks
 
    pairs = [(query, chunk.page_content) for chunk in chunks]
    scores = cross_encoder.predict(pairs)
    

    THRESHOLD = 0.0001

    filtered = [
        (chunk, score)
        for chunk, score in zip(chunks, scores)
        if score >= THRESHOLD
    ]
    print("Original scores:")
    print(scores)

    print("\nFiltered scores:")
    print([score for chunk, score in filtered])

    filtered.sort(key=lambda x: x[1], reverse=True)

    reranked = [chunk for chunk, score in filtered]

    return reranked
