
from sqlalchemy import Column, Integer, Float, String, Text
from .db import Base

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)

    display_name = Column(String(255), index=True, nullable=False)  # 원재료 선택명
    name = Column(String(255), nullable=False)                      # 원재료명
    brand = Column(String(255), default="")                         # 브랜드/제조사
    base_g = Column(Float, default=100.0)                           # 기준량(g)

    sodium_mg_100g = Column(Float, default=0.0)
    carbs_g_100g = Column(Float, default=0.0)
    sugars_g_100g = Column(Float, default=0.0)
    fiber_g_100g = Column(Float, default=0.0)
    allulose_g_100g = Column(Float, default=0.0)
    fat_g_100g = Column(Float, default=0.0)
    trans_fat_g_100g = Column(Float, default=0.0)
    sat_fat_g_100g = Column(Float, default=0.0)
    chol_mg_100g = Column(Float, default=0.0)
    protein_g_100g = Column(Float, default=0.0)

    memo = Column(Text, default="")
