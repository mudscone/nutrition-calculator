
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

# Rounding rules (aligned to your Excel "설정" intent)
ROUND_KCAL = 0
ROUND_MG = 0
ROUND_G = 1

NUTRIENTS_ORDER = [
    ("kcal", "열량(kcal)", "kcal"),
    ("sodium_mg", "나트륨(mg)", "mg"),
    ("carbs_g", "탄수화물(g)", "g"),
    ("sugars_g", "당류(g)", "g"),
    ("fiber_g", "식이섬유(g)", "g"),
    ("allulose_g", "알룰로스(g)", "g"),
    ("fat_g", "지방(g)", "g"),
    ("trans_fat_g", "트랜스지방(g)", "g"),
    ("sat_fat_g", "포화지방(g)", "g"),
    ("chol_mg", "콜레스테롤(mg)", "mg"),
    ("protein_g", "단백질(g)", "g"),
]

def _r(value: float, unit: str) -> float:
    if unit == "kcal":
        return round(value, ROUND_KCAL)
    if unit == "mg":
        return round(value, ROUND_MG)
    return round(value, ROUND_G)

def calc_kcal(carbs_g: float, fiber_g: float, allulose_g: float, protein_g: float, fat_g: float) -> float:
    # User requirement:
    # - digestible carbs at 4 kcal/g (carbs - fiber - allulose, floor at 0)
    # - fiber at 2 kcal/g
    # - allulose at 0 kcal/g
    digestible = max(carbs_g - fiber_g - allulose_g, 0.0)
    kcal = 4.0 * digestible + 2.0 * fiber_g + 4.0 * protein_g + 9.0 * fat_g
    return kcal

def compute_totals(items: List[Dict[str, Any]], unit_weight_g: float) -> Dict[str, Any]:
    """
    items: [{"ingredient": Ingredient, "amount_g": float}, ...]
    unit_weight_g: baked product weight per unit (g)
    Returns dict containing per_unit and per_100g values.
    """
    sums = {
        "sodium_mg": 0.0,
        "carbs_g": 0.0,
        "sugars_g": 0.0,
        "fiber_g": 0.0,
        "allulose_g": 0.0,
        "fat_g": 0.0,
        "trans_fat_g": 0.0,
        "sat_fat_g": 0.0,
        "chol_mg": 0.0,
        "protein_g": 0.0,
    }

    for it in items:
        ing = it["ingredient"]
        amt = float(it["amount_g"] or 0.0)
        factor = amt / 100.0  # per 100g basis
        sums["sodium_mg"] += factor * float(ing.sodium_mg_100g or 0.0)
        sums["carbs_g"] += factor * float(ing.carbs_g_100g or 0.0)
        sums["sugars_g"] += factor * float(ing.sugars_g_100g or 0.0)
        sums["fiber_g"] += factor * float(ing.fiber_g_100g or 0.0)
        sums["allulose_g"] += factor * float(ing.allulose_g_100g or 0.0)
        sums["fat_g"] += factor * float(ing.fat_g_100g or 0.0)
        sums["trans_fat_g"] += factor * float(ing.trans_fat_g_100g or 0.0)
        sums["sat_fat_g"] += factor * float(ing.sat_fat_g_100g or 0.0)
        sums["chol_mg"] += factor * float(ing.chol_mg_100g or 0.0)
        sums["protein_g"] += factor * float(ing.protein_g_100g or 0.0)

    kcal = calc_kcal(
        carbs_g=sums["carbs_g"],
        fiber_g=sums["fiber_g"],
        allulose_g=sums["allulose_g"],
        protein_g=sums["protein_g"],
        fat_g=sums["fat_g"],
    )

    per_unit = {"kcal": kcal, **sums}

    # Convert to per 100g based on unit weight
    per_100g = {}
    if unit_weight_g and unit_weight_g > 0:
        ratio = 100.0 / float(unit_weight_g)
        for k, v in per_unit.items():
            per_100g[k] = v * ratio
    else:
        for k in per_unit.keys():
            per_100g[k] = 0.0

    # Apply rounding
    rounded_unit = {}
    rounded_100g = {}
    for key, label, unit in NUTRIENTS_ORDER:
        rounded_unit[key] = _r(float(per_unit.get(key, 0.0)), unit)
        rounded_100g[key] = _r(float(per_100g.get(key, 0.0)), unit)

    return {
        "order": NUTRIENTS_ORDER,
        "per_unit": rounded_unit,
        "per_100g": rounded_100g,
        "raw_per_unit": per_unit,
        "raw_per_100g": per_100g,
    }
