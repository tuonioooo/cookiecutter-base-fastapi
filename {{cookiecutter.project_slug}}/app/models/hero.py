from pydantic import BaseModel, Field
from typing import List


class HeroBase(BaseModel):
    name: str | None = None
    age: int | None = None
    secret_name: str | None = None


class HeroCreate(HeroBase):
    name: str
    secret_name: str


class HeroUpdate(HeroBase):
    pass


class Hero(HeroBase):
    id: int = Field(...)
    
    class Config:
        from_attributes = True


class HeroQo(BaseModel):
    name: str | None = None
    page: int = 1
    page_size: int = 10


class HeroListResponse(BaseModel):
    total: int
    items: List[Hero]
