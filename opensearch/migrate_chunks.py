"""
Run once (or re-run any time you want to re-sync) to copy chunk texts from
Postgres into OpenSearch:
    python migrate_chunks_to_opensearch.py

Reads resumes.chunk_texts (the JSON list of chunk strings you already
store per resume), joins to candidates on (user_id, filename == source) to
also attach candidate_name, and bulk-indexes one OpenSearch document per
chunk.

This is a standalone script -- it does not touch api.py, crud.py's
behavior, or anything that runs during a normal upload. Run it manually
whenever you want OpenSearch to reflect what's currently in Postgres.
"""

from opensearchpy.helpers import bulk

from opensearch.client import get_client, INDEX_NAME
from db import SessionLocal
from models import Resume, Candidates


def fetch_resumes_with_chunks():
    db = SessionLocal()
    try:
        resumes = db.query(Resume).filter(Resume.chunks.isnot(None)).all()

        # Build a lookup of (user_id, filename) -> candidate_name, so each
        # chunk document can carry the candidate's name for display.
        candidates = db.query(Candidates).all()
        name_lookup = {(c.user_id, c.source): c.name for c in candidates}

        return resumes, name_lookup
    finally:
        db.close()


def build_actions(resumes, name_lookup):
    for resume in resumes:
        if not resume.chunks:
            continue

        name = name_lookup.get((resume.user_id, resume.filename), "Unknown")

        for i, chunks in enumerate(resume.chunks):
            yield {
                "_index": INDEX_NAME,
                "_id": f"{resume.user_id}:{resume.filename}:{i}",  # stable id -- re-running this script overwrites rather than duplicates
                "_source": {
                    "user_id": resume.user_id,
                    "source": resume.filename,
                    "candidate_name": name,
                    "chunk_index": i,
                    "chunk_text": chunks,
                }
            }


if __name__ == "__main__":
    client = get_client()

    resumes, name_lookup = fetch_resumes_with_chunks()
    print(f"Found {len(resumes)} resumes with chunk_texts to index.")

    actions = list(build_actions(resumes, name_lookup))
    print(f"Indexing {len(actions)} chunks into '{INDEX_NAME}'...")

    success_count, errors = bulk(client, actions, raise_on_error=False)
    print(f"Indexed {success_count} chunks successfully.")
    if errors:
        print(f"{len(errors)} errors occurred:")
        for err in errors[:5]:
            print(" ", err)