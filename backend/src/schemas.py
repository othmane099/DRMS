from pydantic import BaseModel


class Error(BaseModel):
    detail: str
    code: int | None


class Message(BaseModel):
    detail: str
