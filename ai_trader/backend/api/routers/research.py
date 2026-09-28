from fastapi import APIRouter

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
