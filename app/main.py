from __future__ import annotations

import json
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import redis

from database.db import SessionLocal
from app.models import Job, JobStatus, Step

# Redis queue settings (local default)
REDIS_URL = "redis://localhost:6379/0"
QUEUE_NAME = "job_queue"

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="AI Workflow Orchestrator")


class CreateJobRequest(BaseModel):
    request_text: str = Field(..., min_length=3, description="What the user wants to do")


class CreateJobResponse(BaseModel):
    job_id: int
    status: str


class StepOut(BaseModel):
    id: int
    tool_name: str
    status: str
    input_json: str | None = None
    output_json: str | None = None
    error_message: str | None = None


class JobOut(BaseModel):
    id: int
    status: str
    request_text: str
    result_text: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str
    steps: list[StepOut] = []


@app.post("/jobs", response_model=CreateJobResponse)
def create_job(payload: CreateJobRequest):
    db = SessionLocal()
    try:
        job = Job(
            status=JobStatus.QUEUED.value,
            request_text=payload.request_text,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Enqueue job_id (simple queue: Redis list)
        r.lpush(QUEUE_NAME, str(job.id))

        return CreateJobResponse(job_id=job.id, status=job.status)
    finally:
        db.close()


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        steps = (
            db.query(Step)
            .filter(Step.job_id == job_id)
            .order_by(Step.id.asc())
            .all()
        )

        return JobOut(
            id=job.id,
            status=job.status,
            request_text=job.request_text,
            result_text=job.result_text,
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            steps=[
                StepOut(
                    id=s.id,
                    tool_name=s.tool_name,
                    status=s.status,
                    input_json=s.input_json,
                    output_json=s.output_json,
                    error_message=s.error_message,
                )
                for s in steps
            ],
        )
    finally:
        db.close()