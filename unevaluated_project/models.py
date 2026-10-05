"""
resumes uploaded from users are stored in postgres database as binary files which can bloat the database size
and storing them in something like s3/local disk is preffered ,
 Since this is not produnction level apllication we will go with storing resummes in postgres itself.
"""

from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey, JSON , Text
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from db import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)  # NEW: needed to scope resumes per user
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=False)  # it stores raw byte files

    chunks = relationship("ResumeChunk", back_populates="resume", cascade="all, delete-orphan")


class Candidates(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    source = Column(String, nullable=False)
    name = Column(String, nullable=False)
    education = Column(String, nullable=True)
    skills = Column(String, nullable=True)  # Store as JSON string
    experience = Column(String, nullable=True)
    projects = Column(String, nullable=True)  # Store as JSON string
    role = Column(String, nullable=True)
    cleaned_text = Column(String, nullable=True)  # Store the cleaned text of the resume


class QueryLog(Base):
    """
    One row per /query call, keeping the full response (including the
    retrieval debug fields already computed in main.py) so you can review
    or evaluate past queries later without re-running them.
    """
    __tablename__ = "query_logs"
 
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    candidates_checked = Column(String, nullable=True)
    retrieved_sources = Column(JSON, nullable=True)   # list of filenames, in ranked order
    final_sources = Column(JSON, nullable=True)        # list of filenames, after metadata filtering
    contexts = Column(JSON, nullable=True)# list of "Candidate: ...\n\n<chunk text>" strings
    correct_response_round_1= Column(Text, nullable=True)
















class ResumeChunk(Base):
    """
    Replaces the in-memory FAISS index. Each chunk of a resume is stored here
    as its own row, with the embedding living directly in Postgres via pgvector.
    Nothing is lost on server restart -- there's no separate index to rebuild.
    """
    __tablename__ = "resume_chunks"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)

    chunk_text = Column(String, nullable=False)
    embedding = Column(Vector(384), nullable=False)  # 384 = all-MiniLM-L6-v2 output size
    chunk_metadata = Column(JSON, nullable=True)  # e.g. {"source": filename, "candidate_name": ...}

    resume = relationship("Resume", back_populates="chunks")