from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel,Field
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from langchain_core.documents import Document
from ingestion import extract_text_from_pdf,clean_resume,candidates_info,chunking
from retriver import create_faiss_index
from filters import resume_match_JD
from main import query
from typing import List
from fastapi.openapi.utils import get_openapi
import json
import os
import numpy as np
import re
from crud import get_candidates, candidate_exists, insert_candidate, delete_candidates, insert_resume, delete_resumes , insert_query_log



load_dotenv()

# --- Auth removed ---
# There is no authentication for now, so every request is treated as
# belonging to this single fixed user. If you add auth back later, replace
# this constant with a value derived from the request (e.g. a Depends()
# function like the old get_current_user).
DEFAULT_USER_ID = "local_user"


model = SentenceTransformer("all-MiniLM-L6-v2")   #embedding model
indexes = {}    # stores each user's faiss index
bm25_indexes = {}  
chunks_by_user = {}   # stores each user's document chunks
extracted_info_by_user = {}    # stores each user's extracted candidate information



@asynccontextmanager 
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="FastAPI",
        version="0.1.0",
        routes=app.routes,
    )
    schema["openapi"] = "3.0.3"
    
    
    for schema_def in schema.get("components", {}).get("schemas", {}).values():
        for field in schema_def.get("properties", {}).values():
            if field.get("type") == "array":
                items = field.get("items", {})
                if "contentMediaType" in items:
                    del items["contentMediaType"]
                    items["type"] = "string"
                    items["format"] = "binary"

    app.openapi_schema = schema
    return app.openapi_schema
app.openapi = custom_openapi



class QueryRequest(BaseModel):
    query: str
class JDRequest(BaseModel):
    job_description: str




def build_user_index(user_id: str):    # this function ensures if users resumes are not currently loaded in memory, it loads them from the database and builds the FAISS index for that user. This is done to avoid loading all users' resumes into memory at once, which could be inefficient and consume a lot of resources.
    
    if user_id in indexes:
        return 
    

    # Replaces: supabase.table("candidates").select("*").eq("user_id", user_id).execute()
    # get_candidates now returns SQLAlchemy ORM objects, so fields are accessed
    # as attributes (candidate.source) instead of dict keys (candidate["source"]).
    candidates = get_candidates(user_id)

    extracted_info_by_user[user_id] = {}
    chunks_by_user[user_id] = []
    indexes[user_id] = None
   
    

    if not candidates:
        print("No candidates found in database!")
        return
    

    for candidate in candidates:
        extracted_info_by_user[user_id][candidate.source] = {
            "Name": candidate.name,
            "Education": candidate.education,
            "Skills": json.loads(candidate.skills) if candidate.skills else [],
            "Experience": candidate.experience,
            "Projects": json.loads(candidate.projects) if candidate.projects else [],
            "Role": candidate.role
        }


    docs = []
    for candidate in candidates:
        if candidate.cleaned_text:
            docs.append(Document(
                page_content=candidate.cleaned_text,
                metadata={"source": candidate.source, "candidate_name": candidate.name}
            ))
    
    

    built_chunks = chunking(docs)
    
    
    for candidate in candidates:
        info = extracted_info_by_user[user_id][candidate.source]
      


    chunks_by_user[user_id] = built_chunks
    indexes[user_id] = create_faiss_index(model, built_chunks)
   
    

    print(f"Loaded {len(candidates)} candidates, built FAISS index with {len(built_chunks)} chunks!")




@app.post("/upload_resume")
async def upload_resume(files: List[UploadFile] = File(...)):
    user_id = DEFAULT_USER_ID

    build_user_index(user_id)

    uploaded_files = []
    skipped_files = [] 

    prompt_injection_detected = False 
    
    for file in files:

        # Replaces: supabase.table("candidates").select("id").eq("user_id", user_id)
        #           .eq("source", file.filename).execute()
        if candidate_exists(user_id, file.filename):
            skipped_files.append(file.filename)
            continue 

        file_content = await file.read()

        # Replaces: supabase.storage.from_("resumes").upload(path=storage_path, file=file_content)
        # Stores the raw resume bytes in Postgres (Resume table) instead of a
        # Supabase Storage bucket or local disk.
        insert_resume(user_id, file.filename, file.content_type, file_content)

        temp_path = f"temp_{file.filename}"

        with open(temp_path, "wb") as f:
            f.write(file_content)

        raw_text = extract_text_from_pdf(temp_path)
        


        injection_patterns = [
        r'SYSTEM\s*:.*?\.',
        r'ignore\s*(all\s*)?(previous\s*)?instructions.*?\.',
        r'you\s*are\s*now.*?\.',
        r'override\s*(previous\s*)?instructions.*?\.',
        r'forget\s*your\s*role.*?\.',
        r'rate\s*this\s*candidate.*?\.',
        r'ignore.*instruction',
        r'previous.*instruction',
        r'act as',
        r'pretend to be',
        r'override',
        r'forget your role',
        r'follow these instructions',
        r'new instructions',
       
        ]

        detected_patterns = []

        
        for pattern in injection_patterns:
            if re.search(pattern, raw_text, flags=re.IGNORECASE):
                prompt_injection_detected = True
                detected_patterns.append(pattern)
                raw_text = re.sub(pattern, "", raw_text, flags=re.IGNORECASE)
            
        

        os.remove(temp_path)

        candidate_info = candidates_info(raw_text)
        
        
        
        cleaned_text = clean_resume(raw_text)
        
       
        
        # Replaces: supabase.table("candidates").insert({...}).execute()
        insert_candidate(
            user_id=user_id,
            source=file.filename,
            name=candidate_info.get("Name"),
            education=candidate_info.get("Education"),
            skills_json=json.dumps(candidate_info.get("Skills", [])),
            experience=candidate_info.get("Experience"),
            projects_json=json.dumps(candidate_info.get("Projects", [])),
            role=candidate_info.get("Role"),
            cleaned_text=cleaned_text
        )
        

        extracted_info_by_user[user_id][file.filename] = candidate_info

        new_doc = Document(
            page_content=cleaned_text,
            metadata={
            "source": file.filename,
            "candidate_name": candidate_info.get("Name")
        }
        )

        new_chunks = chunking([new_doc])

        #cred_chunk = build_credentials_chunk(file.filename, candidate_info.get("Name"), candidate_info)
        #new_chunks.append(cred_chunk)

        chunks_by_user[user_id].extend(new_chunks)
        


        texts = [chunk.page_content for chunk in new_chunks]
        embeddings = model.encode(texts)
        embeddings = np.array(embeddings).astype("float32")

        if indexes[user_id] is None:
            indexes[user_id] = create_faiss_index(model, new_chunks)
        else:
            indexes[user_id].add(embeddings)

        

        uploaded_files.append(file.filename)
        
       

    return {
        "message": " Resume uploaded successfully",
        "security_warning": (
        "Suspicious AI instructions were detected and removed."
        if prompt_injection_detected else None
    )}





@app.post("/query")
async def query_endpoint(request: QueryRequest):
    user_id = DEFAULT_USER_ID
    build_user_index(user_id)
    
    if not extracted_info_by_user[user_id]:
        raise HTTPException(status_code=400, detail="No resumes uploaded yet!")
    
    
    result =  query(
        request.query,
        model,
        indexes[user_id],
       
        chunks_by_user[user_id],
        extracted_info_by_user[user_id]
        )

    insert_query_log(user_id, request.query, result)

    return result



@app.post("/resume-match")
def match_candidates(request: JDRequest):
    user_id = DEFAULT_USER_ID
    build_user_index(user_id)
 
    if not extracted_info_by_user[user_id]:
        raise HTTPException(status_code=400, detail="No resumes uploaded yet!")
 
    
    results = resume_match_JD(request.job_description, extracted_info_by_user[user_id])

    results = [r for r in results if r["score"] > 0]
 
    if not results:
        return {"message": "No matching candidates found"}
 
    return {"matches": results[:5]}





@app.delete("/clear")
def clear_all():
    user_id = DEFAULT_USER_ID

    # Replaces: supabase.table("candidates").delete().eq("user_id", user_id).execute()
    delete_candidates(user_id)

    # Replaces: supabase.storage.from_("resumes").list(...) + .remove([...])
    # Deletes this user's resume rows from Postgres instead of a storage bucket.
    delete_resumes(user_id)

    indexes.pop(user_id, None)
  
    chunks_by_user.pop(user_id, None)
    extracted_info_by_user.pop(user_id, None)

    return {"message": "All resumes cleared"}