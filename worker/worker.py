from __future__ import annotations

import json
import time
from datetime import datetime
import threading

from matplotlib.pyplot import step

import redis

from sqlalchemy import update
from database.db import SessionLocal
from app.models import Job, JobStatus, Step, StepStatus
from tools.registry import get_tool

REDIS_URL = "redis://localhost:6379/0"
QUEUE_NAME = "job_queue"

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def now():
    return datetime.utcnow()

def run_with_timeout(fn, inp: dict, timeout_sec: float):
    """
    Runs a tool function with timeout using a thread.
    Returns (output_dict, error_str).
    """
    result_container = {"out": None, "err": None}

    def target():
        try:
            out, err = fn(inp)
            result_container["out"] = out
            result_container["err"] = err
        except Exception as e:
            result_container["err"] = str(e)

    t = threading.Thread(target=target)
    t.start()
    t.join(timeout=timeout_sec)

    if t.is_alive():
        return {}, f"tool timeout after {timeout_sec}s"

    return result_container["out"], result_container["err"]

def run_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        # Atomic claim: only one worker can move QUEUED -> RUNNING
        stmt = (
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.QUEUED.value)
            .values(status=JobStatus.RUNNING.value, updated_at=now())
        )

        res = db.execute(stmt)
        db.commit()

        if res.rowcount == 0:
            # Someone else already claimed it OR it doesn't exist OR it is already done.
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                print(f"[Worker] Job {job_id} not found. Skipping.")
            else:
                print(f"[Worker] Job {job_id} not claimable (status={job.status}). Skipping.")
            return

        # Re-fetch the job after claim
        job = db.query(Job).filter(Job.id == job_id).first()

        # For MVP: define a fixed workflow = one step: echo
        # Define workflow plan (static for now)
        workflow_plan = [
            {
                "tool_name": "echo",
                "input": {"text": job.request_text}
            },
            {
                "tool_name": "unstable",
                "input": {"sleep_sec": 0.5, "fail_prob": 0.3}
            },
            {
                "tool_name": "echo",
                "input": {"final": "processing completed"}
            }
        ]
        previous_output = None

        for step_def in workflow_plan:
            step = Step(
                job_id=job.id,
                status=StepStatus.PENDING.value,
                tool_name=step_def["tool_name"],
                input_json=json.dumps(step_def["input"]),
                created_at=now(),
                updated_at=now(),
            )
            db.add(step)
            db.commit()
            db.refresh(step)

            # Run this step using existing retry + timeout logic
            step.status = StepStatus.RUNNING.value
            step.updated_at = now()
            db.commit()

            tool = get_tool(step.tool_name)
            if tool is None:
                raise RuntimeError(f"Unknown tool: {step.tool_name}")

            inp = json.loads(step.input_json)

            MAX_RETRIES = 3
            TIMEOUT_SEC = 2.0

            attempt = 0
            success = False
            last_error = None

            while attempt < MAX_RETRIES:
                attempt += 1

                # Heartbeat
                job.updated_at = now()
                step.updated_at = now()
                db.commit()

                out, err = run_with_timeout(tool, inp, TIMEOUT_SEC)

                if err is None:
                    success = True
                    break

                last_error = err
                time.sleep(0.5 * attempt)

            if not success:
                step.status = StepStatus.FAILED.value
                step.error_message = last_error
                step.updated_at = now()

                job.status = JobStatus.FAILED.value
                job.error_message = f"Step {step.tool_name} failed: {last_error}"
                job.updated_at = now()
                db.commit()
                return

            step.output_json = json.dumps(out)
            step.status = StepStatus.SUCCEEDED.value
            step.updated_at = now()
            db.commit()

            previous_output = out
        
        job.result_text = json.dumps(previous_output, indent=2)
        job.status = JobStatus.SUCCEEDED.value
        job.updated_at = now()
        db.commit()

        print(f"[Worker] Job {job_id} completed multi-step workflow.")

    except Exception as e:
        # Hard failure: mark job failed
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.updated_at = now()
            db.commit()
        print(f"[Worker] Job {job_id} crashed: {e}")
    finally:
        db.close()


def main():
    print("[Worker] Starting worker. Waiting for jobs... (Ctrl+C to stop)")
    while True:
        # BRPOP blocks until something is available
        item = r.brpop(QUEUE_NAME, timeout=5)
        if item is None:
            continue

        _, job_id_str = item
        try:
            job_id = int(job_id_str)
        except ValueError:
            print(f"[Worker] Bad job id in queue: {job_id_str}")
            continue

        run_job(job_id)


if __name__ == "__main__":
    main()