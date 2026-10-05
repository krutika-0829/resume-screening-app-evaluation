#from sentence_transformers import SentenceTransformer
# from retriver import create_faiss_index
# from ingestion import load_documents,clean_documents,chunking,store_extracted_info
from filters import metadata_filtering,resume_match_JD
from retriver import retrieve_chunks,rerank_chunks,cap_per_document
from llm import query_response
import json
# import time 
from opensearch.bm25 import search



# documents = load_documents("docs")
# docs = clean_documents(documents) 
# chunks = chunking(docs)
# extracted_info = store_extracted_info()

# model = SentenceTransformer("all-MiniLM-L6-v2")

# index = create_faiss_index(model, chunks)


 
def dedupe_sources(chunk_list):
    """
    Collapse a ranked list of chunks down to a ranked list of unique
    resume source filenames, keeping the position of each resume's
    first (best-scoring) chunk. Used for retrieval evaluation.
    """
    seen = set()
    ordered = []
    for chunk in chunk_list:
        src = chunk.metadata["source"]
        if src not in seen:
            seen.add(src)
            ordered.append(src)
    return ordered
 



def query(query_text, model, index, chunks, extracted_info):
    print(query_text)

   
 
    allowed_sources = metadata_filtering(query_text, extracted_info)
   

    

    if not allowed_sources:
        
        allowed_sources = set(extracted_info.keys())


   
    retrieved_chunks_vector_search = retrieve_chunks(query_text, model, index, chunks, k=10)
    print("retrieved_chunks_vector_search : ", retrieved_chunks_vector_search )

    retrieved_chunks_keyword_search = search(query_text, user_id=None, k=10)
    print("retrieved_chunks_keyword_search : ", retrieved_chunks_keyword_search )

    retrieved_chunks = (
    retrieved_chunks_vector_search
    + retrieved_chunks_keyword_search
)

    retrieved_context = cap_per_document(retrieved_chunks, k=15, max_per_doc=2)
    retrieved_context = rerank_chunks(query_text,retrieved_context )
    
    

    print("retrieved_context : ", retrieved_context )
    

        


    if len(extracted_info) == 1:
        final_chunks = retrieved_context
 
    else:
        
        
 
        if allowed_sources:
            final_chunks = []
            for chunk in retrieved_context:
                if chunk.metadata["source"] in allowed_sources:
                    final_chunks.append(chunk)
        else:
            final_chunks = retrieved_context
 
    
 
    total = len(extracted_info)
    searched = len(allowed_sources)
    candidates_checked = f"{searched}/{total}"
 
    context_text = "\n\n".join([
        f"Candidate: {chunk.metadata['candidate_name']}\n{chunk.page_content}"
        for chunk in final_chunks
    ])
 
 
    Answer = query_response(query_text, context_text)
    
 
    try:
        parsed = json.loads(Answer)
    except:
        parsed = {"Answer": Answer}
 
    parsed["candidates_checked"] = candidates_checked

    parsed["retrieved_sources"] = dedupe_sources(retrieved_context)
    parsed["final_sources"] = dedupe_sources(final_chunks)
    parsed["contexts"] = [
    f"Candidate: {chunk.metadata.get('candidate_name', 'Unknown')}\n\n{chunk.page_content}"
    for chunk in final_chunks
    ]
    
 
 
    return parsed
    

    
def JD_query():
    query = input("Enter Job Description : ")
    results = resume_match_JD(query)
    if not results:
        return {"message": "No matching candidates found"}
    return results[:5]
    


