"""
Database access helpers, built on the SQLAlchemy engine/session in db.py and
the ORM models in models.py.

Same function names as the psycopg2 version from before, so api.py barely
changes -- only the implementation underneath is different.

Note: pgvector-based retrieval (the ResumeChunk table in models.py) is not
wired in here. Per your call, we're skipping that for now and keeping the
in-memory FAISS index in retriver.py exactly as it is.
"""

from db import SessionLocal
from models import Candidates, Resume, QueryLog


def get_candidates(user_id):
    """
    Returns all Candidates rows for this user, as ORM objects
    (attribute access, e.g. candidate.source, not candidate["source"]).
    """
    db = SessionLocal()
    try:
        return db.query(Candidates).filter(Candidates.user_id == user_id).all()
    finally:
        db.close()


def candidate_exists(user_id, filename):
    db = SessionLocal()
    try:
        return db.query(Candidates.id).filter(
            Candidates.user_id == user_id,
            Candidates.source == filename
        ).first() is not None
    finally:
        db.close()


def insert_candidate(user_id, source, name, education, skills_json,
                      experience, projects_json, role, cleaned_text):
    db = SessionLocal()
    try:
        candidate = Candidates(
            user_id=user_id,
            source=source,
            name=name,
            education=education,
            skills=skills_json,
            experience=experience,
            projects=projects_json,
            role=role,
            cleaned_text=cleaned_text,
        )
        db.add(candidate)
        db.commit()
    finally:
        db.close()


def delete_candidates(user_id):
    db = SessionLocal()
    try:
        db.query(Candidates).filter(Candidates.user_id == user_id).delete()
        db.commit()
    finally:
        db.close()


def insert_resume(user_id, filename, content_type, file_data):
    """
    Stores the raw resume file bytes directly in Postgres (Resume table),
    per your call to go with binary-in-Postgres instead of local disk.
    """
    db = SessionLocal()
    try:
        resume = Resume(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_data=file_data,
        )
        db.add(resume)
        db.commit()
    finally:
        db.close()


def delete_resumes(user_id):
    db = SessionLocal()
    try:
        db.query(Resume).filter(Resume.user_id == user_id).delete()
        db.commit()
    finally:
        db.close()



def insert_query_log(user_id, query_text, parsed_response):
    """
    Stores a query and its full parsed response -- answer, candidates_checked,
    retrieved_sources, final_sources, contexts -- exactly as main.py's
    query() already builds them, so nothing about that logic changes.
    """
    db = SessionLocal()
    try:
        log = QueryLog(
            user_id=user_id,
            query_text=query_text,
            answer=parsed_response.get("Answer") or parsed_response.get("answer"),
            candidates_checked=parsed_response.get("candidates_checked"),
            retrieved_sources=parsed_response.get("retrieved_sources"),
            final_sources=parsed_response.get("final_sources"),
            contexts=parsed_response.get("contexts"),
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


        