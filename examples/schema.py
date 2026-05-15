"""Schema matching the sample data in examples/input.*."""

from pydantic import BaseModel


class RowSchema(BaseModel):
    class Address(BaseModel):
        city: str | None = None
        zip: str | None = ""

    id: int
    name: str
    email: str
    age: int
    active: bool
    address: Address | None = None
