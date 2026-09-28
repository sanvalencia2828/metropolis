from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/run", tags=["run"])
def get_last_run() -> dict[str, Any]:
    """Read-only stub for the last execution state."""
    return {"status": "not_implemented", "message": "Run tracking is not available in this phase."}


@router.post("/run", tags=["run"], status_code=501)
def trigger_run() -> dict[str, Any]:
    """Execution trigger stub disabled for this phase."""
    raise HTTPException(status_code=501, detail="Run execution is not implemented yet.")
