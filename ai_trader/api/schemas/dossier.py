from pydantic import BaseModel


class DossierResponse(BaseModel):
    status: str = "not_implemented"
    message: str = "Dossier viewer is not available in this phase."
