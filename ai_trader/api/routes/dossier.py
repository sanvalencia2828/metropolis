from fastapi import APIRouter

router = APIRouter()


@router.get("/dossier", tags=["dossier"])
def get_dossier() -> dict:
    """Dossier endpoint stub."""
    return {"status": "not_implemented", "message": "Dossier viewer is not available in this phase."}
