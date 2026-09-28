from pydantic import BaseModel


class TokenQuery(BaseModel):
    chain: str = "sol"
    address: str
