import re 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

import json
from langchain_community.document_loaders import DirectoryLoader,PyPDFLoader
import os
from llm import extract_info
from collections import defaultdict
import fitz
import datetime

def load_documents(docs_path = "docs"):

  
    if not os.path.exists(docs_path):
       raise FileNotFoundError(f"The directory {docs_path} does not exist.")
    
    
    loader = DirectoryLoader(
    path = docs_path,
    glob="*.pdf",
    loader_cls= PyPDFLoader
    )
    documents = loader.load()
    
    return documents






def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)

    raw_text = ""
    for page in doc:
        raw_text += page.get_text()

    doc.close()
    return raw_text


def clean_resume(resume):
    


    # Remove extra spaces/tabs but keep line breaks
    data_space_removed = re.sub(r'[ \t]+', ' ', resume)

    # Replace multiple empty lines with a single newline
    cleaned_data = re.sub(r'\n+', '\n', data_space_removed)

    return cleaned_data.strip()



def group_docs_per_resume():
    documents = load_documents("docs")
    grouped_docs = defaultdict(list) 
    for doc in documents:
        source = doc.metadata["source"]
        grouped_docs[source].append(doc.page_content) 
    return grouped_docs 


from datetime import datetime

def compute_years_of_experience(work_experiences):
    """
    Years of experience = the union of all employment intervals, not the
    span and not a naive sum:
      - overlapping/concurrent roles aren't double-counted
      - gaps between roles aren't counted as experience
    """
    current_year = datetime.now().year
    intervals = []

    for exp in work_experiences:
        start = exp.get("startYear")
        if start is None:
            continue
        end = current_year if exp.get("isCurrent") else (exp.get("endYear") or start)
        if end < start:
            continue  # inconsistent data, skip rather than produce a negative interval
        intervals.append((start, end))

    if not intervals:
        return None

    intervals.sort()
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:          # overlapping or touching -> merge
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return sum(end - start for start, end in merged)


 
 
def candidates_info(context):
 
    info = extract_info(context)
    try:
        parsed = json.loads(info)
    except (json.JSONDecodeError, TypeError):
        # Only a genuine JSON-parse failure lands here -- this error path
        # must stay separate from the computation below, so a years-of-
        # experience bug can never masquerade as (or swallow a successful)
        # JSON parse.
        return {"error": "Invalid JSON", "raw": info}
 
    try:
        parsed["yearsOfExperience"] = compute_years_of_experience(parsed.get("workExperiences", []))
    except Exception:
        # A malformed workExperiences entry (e.g. non-integer startYear)
        # shouldn't discard the rest of a otherwise-good extraction.
        parsed["yearsOfExperience"] = None
 
    return parsed
    

def store_extracted_info():
 
 if os.path.exists("extracted_info.json"):

    with open("extracted_info.json", "r") as f:

        all_resume_info = json.load(f)

    print("Loaded from cache!")

 else:

    all_resume_info = {}

    context = group_docs_per_resume()

    for source, pages in context.items():

        print(f"Processing: {source}")
        full_resume = "\n".join(pages)
        info = candidates_info(full_resume)
        all_resume_info[source] = info

    with open("extracted_info.json", "w") as f:
        json.dump(all_resume_info, f,indent=4)
 return all_resume_info









def clean_documents(documents):
    
    docs = []
    for doc in documents:
        cleaned_text = clean_resume(doc.page_content)

        source = doc.metadata["source"]

        extracted_info = store_extracted_info()

        candidate_name = extracted_info.get(source, {}).get("Name", "Unknown")
     
        doc = Document(
        page_content = cleaned_text,
        metadata = {
            **doc.metadata,
            "candidate_name": candidate_name
            
        }
        )
        docs.append(doc)

    return docs







def chunking(docs):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 400,
        chunk_overlap = 75
    )

    chunks = splitter.split_documents(docs)

    return chunks 


# def build_credentials_chunk(source, candidate_name, candidate_info):
#     """
#     One dense, always-present chunk per resume containing just the core
#     facts -- separate from the regular 400-char sliding-window chunks,
#     so sparse categorical facts (PhD, IIT, etc.) don't get diluted.
#     """
#     text = (
#         f"Name: {candidate_info.get('Name', '')}\n"
#         f"Education: {candidate_info.get('Education', '')}\n"
#         f"Role: {candidate_info.get('Role', '')}\n"
#         f"Skills: {', '.join(candidate_info.get('Skills', []))}"
#     )
#     return Document(
#         page_content=text,
#         metadata={"source": source, "candidate_name": candidate_name}
   # )