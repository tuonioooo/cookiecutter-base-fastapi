from typing import Annotated

from fastapi import APIRouter, Query
# from sqlalchemy import select
from sqlmodel import select
from ..core.crud import CRUDBase
from ..core.database.db_manager import DbSessionDep
from ..models import Hero, HeroQo

router = APIRouter(
    prefix="/heroes",
    tags=["简单示例"],
)
hero_crud = CRUDBase[Hero, int](Hero)

"""
注意：
依赖项-Depends嵌套问题
https://www.yuque.com/g/tuonioooo/cyaz9e/oavi27va0nob0826/collaborator/join?token=DATcLE3m44qsqA4R&source=doc_collaborator# 《依赖项-Depends补充》
"""


@router.post("/")
def create_hero(hero_qo: HeroQo, session: DbSessionDep):
    return hero_crud.create(session, Hero(**hero_qo.model_dump(exclude_unset=True)))  # 仅提取非默认值的字段（避免覆盖未传字段）


@router.get("/")
def read_heroes(
        session: DbSessionDep,
        offset: int = 0,
        limit: Annotated[int, Query(le=100)] = 100,
) -> list[Hero]:
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes


@router.get("/get/{hero_id}")
def read_hero(hero_id: int, session: DbSessionDep):
    return hero_crud.read(session, hero_id)


@router.put("/update/{hero_id}")
def update_hero(hero_id: int, hero_qo: HeroQo, session: DbSessionDep):
    return hero_crud.update(session, hero_id, Hero(**hero_qo.model_dump(exclude_unset=True)))


@router.delete("/delete/{hero_id}")
def delete_hero(hero_id: int, session: DbSessionDep):
    hero_crud.delete(session, hero_id)
    return {"ok": True}
