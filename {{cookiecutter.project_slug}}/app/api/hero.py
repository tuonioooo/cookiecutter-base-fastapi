from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..models.hero import Hero, HeroCreate, HeroUpdate, HeroQo, HeroListResponse

router = APIRouter(
    prefix="/heroes",
    tags=["hero"]
)

# 模拟数据库
fake_heroes_db = [
    Hero(id=1, name="钢铁侠", age=40, secret_name="托尼·斯塔克"),
    Hero(id=2, name="蜘蛛侠", age=18, secret_name="彼得·帕克"),
    Hero(id=3, name="美国队长", age=100, secret_name="史蒂夫·罗杰斯"),
    Hero(id=4, name="雷神", age=1500, secret_name="托尔·奥丁森"),
    Hero(id=5, name="黑寡妇", age=35, secret_name="娜塔莎·罗曼诺夫"),
]


@router.get("", response_model=HeroListResponse)
async def get_heroes(
    query: Annotated[HeroQo, Depends()]
)-> list[HeroListResponse]:
    """获取英雄列表"""
    filtered_heroes = fake_heroes_db
    
    # 按名称过滤
    if query.name:
        filtered_heroes = [hero for hero in filtered_heroes if query.name.lower() in hero.name.lower()]
    
    # 计算分页
    start = (query.page - 1) * query.page_size
    end = start + query.page_size
    
    return HeroListResponse(
        total=len(filtered_heroes),
        items=filtered_heroes[start:end]
    )


@router.get("/{hero_id}", response_model=Hero)
async def get_hero(hero_id: int):
    """获取单个英雄详情"""
    for hero in fake_heroes_db:
        if hero.id == hero_id:
            return hero
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"未找到ID为{hero_id}的英雄"
    )


@router.post("", response_model=Hero)
async def create_hero(hero: HeroCreate):
    """创建新英雄"""
    # 模拟ID自增
    new_id = max(hero.id for hero in fake_heroes_db) + 1 if fake_heroes_db else 1
    new_hero = Hero(id=new_id, **hero.model_dump())
    fake_heroes_db.append(new_hero)
    return new_hero


@router.put("/{hero_id}", response_model=Hero)
async def update_hero(hero_id: int, hero_data: HeroUpdate):
    """更新英雄信息"""
    for i, hero in enumerate(fake_heroes_db):
        if hero.id == hero_id:
            # 过滤掉None值，只更新提供的字段
            update_data = {k: v for k, v in hero_data.model_dump().items() if v is not None}
            # 获取当前英雄数据的副本
            hero_dict = hero.model_dump()
            # 更新英雄数据
            hero_dict.update(update_data)
            # 创建更新后的英雄对象
            updated_hero = Hero(**hero_dict)
            fake_heroes_db[i] = updated_hero
            return updated_hero
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"未找到ID为{hero_id}的英雄"
    )


@router.delete("/{hero_id}")
async def delete_hero(hero_id: int):
    """删除英雄"""
    for i, hero in enumerate(fake_heroes_db):
        if hero.id == hero_id:
            del fake_heroes_db[i]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": f"英雄 ID {hero_id} 已成功删除"}
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"未找到ID为{hero_id}的英雄"
    )
