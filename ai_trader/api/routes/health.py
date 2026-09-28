from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health() -> dict:
    """Health-check endpoint stub."""
    return {"status": "ok"}
