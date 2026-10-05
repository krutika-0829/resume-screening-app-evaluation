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
from models import Candidates, Resume, QueryLog, EvaluatedQueryLog


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


def delete_candidate(user_id, filename):
    """Deletes a single candidate row (one resume) for this user, by filename."""
    db = SessionLocal()
    try:
        db.query(Candidates).filter(
            Candidates.user_id == user_id,
            Candidates.source == filename
        ).delete()
        db.commit()
    finally:
        db.close()


def delete_resume_by_filename(user_id, filename):
    """Deletes a single resume's stored file bytes for this user, by filename."""
    db = SessionLocal()
    try:
        db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.filename == filename
        ).delete()
        db.commit()
    finally:
        db.close()


def insert_candidate(user_id, source, name, email, phone, location, role, bio,
                      linkedin_url, github_url, work_experiences, educations,
                      skills, years_of_experience, cleaned_text):
    """
    Matches the current Candidates model: work_experiences, educations, and
    skills are native JSON columns now -- pass them as plain Python
    lists/dicts, no json.dumps() needed. There's no `projects` field on this
    model anymore, since RESUME_TOOL doesn't extract it.
    """
    db = SessionLocal()
    try:
        candidate = Candidates(
            user_id=user_id,
            source=source,
            name=name,
            email=email,
            phone=phone,
            location=location,
            role=role,
            bio=bio,
            linkedin_url=linkedin_url,
            github_url=github_url,
            work_experiences=work_experiences,
            educations=educations,
            skills=skills,
            years_of_experience=years_of_experience,
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


def insert_resume(user_id, filename, content_type, file_data,cleaned_text,raw_text=None, chunks=None, chunk_embeddings=None):
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
            cleaned_text=cleaned_text,
            raw_text=raw_text,
            chunks=chunks,
            chunk_embeddings=chunk_embeddings,
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


def insert_evaluated_query_log(user_id, query_text, parsed_response):
    """
    Same as insert_query_log, but writes to evaluated_query_logs instead --
    used for a second round of queries (e.g. after re-uploading resumes) so
    it can be compared against the original query_logs row for the same
    question without overwriting it.
    """
    db = SessionLocal()
    try:
        log = EvaluatedQueryLog(
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