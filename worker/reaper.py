from __future__ import annotations

from datetime import datetime, timedelta

from database.db import SessionLocal
from app.models import Job, JobStatus, Step, StepStatus


def now():
    return datetime.utcnow()


def reap_stale_jobs(max_running_minutes: int = 5) -> int:
    """
    Mark RUNNING jobs as FAILED if they haven't updated in max_running_minutes.
    This is a simple self-healing mechanism.
    """
    cutoff = now() - timedelta(minutes=max_running_minutes)

    db = SessionLocal()
    try:
        stale_jobs = (
            db.query(Job)
            .filter(Job.status == JobStatus.RUNNING.value)
            .filter(Job.updated_at < cutoff)
            .all()
        )

        count = 0
        for job in stale_jobs:
            job.status = JobStatus.FAILED.value
            job.error_message = f"Reaper: job stuck in RUNNING since {job.updated_at.isoformat()} (cutoff {cutoff.isoformat()})"
            job.updated_at = now()

            # Mark any RUNNING/PENDING steps as failed too (optional but useful)
            steps = (
                db.query(Step)
                .filter(Step.job_id == job.id)
                .filter(Step.status.in_([StepStatus.PENDING.value, StepStatus.RUNNING.value]))
                .all()
            )
            for s in steps:
                s.status = StepStatus.FAILED.value
                s.error_message = "Reaper: step abandoned due to stale job"
                s.updated_at = now()

            count += 1

        db.commit()
        return count
    finally:
        db.close()


def main():
    # Start conservative: 2 minutes for debugging.
    # In real systems you set this based on expected runtime.
    max_minutes = 2
    n = reap_stale_jobs(max_running_minutes=max_minutes)
    print(f"[Reaper] Marked {n} stale RUNNING jobs as FAILED (threshold={max_minutes} minutes)")


if __name__ == "__main__":
    main()