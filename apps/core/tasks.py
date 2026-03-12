"""Async tasks for the audit engine — runs via Huey task queue."""
from huey.contrib.djhuey import task


@task()
def run_audit_async(project_id: int) -> int:
    """Run audit in background via Huey. Returns AuditReport.id."""
    from .audit_engine import run_audit
    return run_audit(project_id)
