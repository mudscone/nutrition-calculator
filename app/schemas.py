
from pydantic import BaseModel

class IngredientIn(BaseModel):
    name: str
    brand: str = ""
    base_g: float = 100.0
    sodium_mg_100g: float = 0.0
    carbs_g_100g: float = 0.0
    sugars_g_100g: float = 0.0
    fiber_g_100g: float = 0.0
    allulose_g_100g: float = 0.0
    fat_g_100g: float = 0.0
    trans_fat_g_100g: float = 0.0
    sat_fat_g_100g: float = 0.0
    chol_mg_100g: float = 0.0
    protein_g_100g: float = 0.0
    memo: str = ""
