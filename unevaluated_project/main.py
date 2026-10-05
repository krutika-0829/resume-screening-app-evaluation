#from sentence_transformers import SentenceTransformer
from retriver import create_faiss_index
from ingestion import load_documents,clean_documents,chunking,store_extracted_info
from filters import metadata_filtering,resume_match_JD
from retriver import retrieve_chunks,rerank_chunks
from llm import query_response
import json
import time 



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

    #total_start = time.perf_counter()
    #metadata_start = time.perf_counter()
 
    allowed_sources = metadata_filtering(query_text, extracted_info)
    #metadata_time = time.perf_counter() - metadata_start

    

    if not allowed_sources:
        
        allowed_sources = set(extracted_info.keys())


    #retrieval_start = time.perf_counter()
    retrieved_chunks = retrieve_chunks(query_text, model, index, chunks, k=10)
    print(retrieved_chunks)


    
    #retrieval_time = time.perf_counter() - retrieval_start

   
   
    
    
    
    
    #rerank_start = time.perf_counter()
    retrieved_context = rerank_chunks(query_text,retrieved_chunks )
    #rerank_time = time.perf_counter() - rerank_start
        


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
 
    #llm_start = time.perf_counter()
    Answer = query_response(query_text, context_text)
    #llm_time = time.perf_counter() - llm_start
 
    try:
        parsed = json.loads(Answer)
    except:
        parsed = {"Answer": Answer}
 
    parsed["candidates_checked"] = candidates_checked
 
    # === ADDED FOR EVALUATION ===
    parsed["retrieved_sources"] = dedupe_sources(retrieved_context)
    parsed["final_sources"] = dedupe_sources(final_chunks)
    parsed["contexts"] = [
    f"Candidate: {chunk.metadata.get('candidate_name', 'Unknown')}\n\n{chunk.page_content}"
    for chunk in final_chunks
]
    
   
    #total_time = time.perf_counter() - total_start

    #print("\n========== LATENCY ==========")
    #print(f"Metadata Filtering : {metadata_time:.3f} sec")
    #print(f"FAISS Retrieval    : {retrieval_time:.3f} sec")
    #print(f"Reranking          : {rerank_time:.3f} sec")
    
    #print(f"LLM Generation     : {llm_time:.3f} sec")
    #print(f"Total Query Time   : {total_time:.3f} sec")
   # print("=============================\n")
    # =============================
 
    return parsed
    

    
def JD_query():
    query = input("Enter Job Description : ")
    results = resume_match_JD(query)
    if not results:
        return {"message": "No matching candidates found"}
    return results[:5]
    


# def query(query_text,model,index,chunks,extracted_info): 
   
   
#     retrieved_context , similarity_scores = retrieve_chunks(query_text,model,index,chunks,k=5)
    
#     retrieval_score = round(sum(sorted(similarity_scores, reverse=True)[:3]) / 3, 2)
    # print("RETRIVED_CONTEXT : " ,retrieved_context)
    
 


    # if len(extracted_info) == 1:
    #     final_chunks = retrieved_context

    # else:
    #     allowed_sources = metadata_filtering(query_text,extracted_info)
    #     print("ALLOWED_SOURCES : ",allowed_sources)
        

    #     if allowed_sources:

    #         final_chunks = []

    #         for chunk in retrieved_context:
    #             if chunk.metadata["source"] in allowed_sources:
    #                 final_chunks.append(chunk)

    #     else:
    #         final_chunks = retrieved_context
   
    # print("FINAL_CHUNKS : " ,final_chunks)
    
    

#     context_text = "\n\n".join([
#     f"Candidate: {chunk.metadata['candidate_name']}\n{chunk.page_content}" 
#     for chunk in final_chunks
# ])
#     Answer = query_response(query_text, context_text)
    
   
#     try:
#         parsed = json.loads(Answer)
#         return parsed
        
#     except Exception as e:
        
#         return {"answer": Answer}