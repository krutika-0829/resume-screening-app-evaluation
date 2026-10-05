"""
Run this once to create the tables the app currently needs:
    python init_db.py

Only creates `candidates` and `resumes`. `resume_chunks` (pgvector) is
skipped on purpose -- we're not using pgvector retrieval yet, and creating
that table requires the Postgres "vector" extension to be enabled first.
When you're ready for that, run:
    CREATE EXTENSION IF NOT EXISTS vector;
in your database, then include ResumeChunk.__table__ below.
"""

from db import engine, Base
from models import Candidates, Resume, QueryLog, EvaluatedQueryLog

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine, tables=[Candidates.__table__, Resume.__table__, QueryLog.__table__, EvaluatedQueryLog.__table__])
    print("Created tables: candidates, resumes, query_logs, evaluated_query_logs")