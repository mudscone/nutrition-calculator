
import os
import re

from datetime import datetime
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv()



from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi import Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .db import SessionLocal, init_db
from .models import Ingredient
from .auth import require_admin, verify_admin_password
from .schemas import IngredientIn
from .services.calc import compute_totals
from .services.pdf import build_label_pdf
from sqlalchemy import case, func

BRAND_NAME = os.getenv("BRAND_NAME", "영양성분 계산기")



app = FastAPI(title=BRAND_NAME)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "change-me-please"))
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def _startup():
    init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_recipe_session(request: Request) -> Dict[str, Any]:
    if "recipe" not in request.session:
        request.session["recipe"] = {
            "recipe_name": "",
            "unit_weight_g": 0.0,
            "items": []  # list of {"ingredient_id": int, "amount_g": float}
        }
    return request.session["recipe"]


import re

@app.get("/", response_class=HTMLResponse)
def recipe_form(request: Request, db=Depends(get_db)):
    recipe = _get_recipe_session(request)

    # DB에서 전부 가져온 뒤, Python에서 정렬(로컬/배포 동일 결과)
    ingredients = db.query(Ingredient).all()

    def sort_name(display_name: str) -> str:
        s = (display_name or "").strip()
        # '이눌린|OO' 같은 형태면 앞부분만 정렬 기준으로 사용
        if "|" in s:
            s = s.split("|", 1)[0].strip()
        return s

    def strip_leading_symbols(s: str) -> str:
        # 공백/기호가 앞에 있으면 정렬을 망치니 제거
        return re.sub(r"^[^0-9A-Za-z가-힣]+", "", s)

    def is_english_start(s: str) -> bool:
        return bool(s) and s[0].isascii() and s[0].isalpha()

    def key(ing: Ingredient):
        s = strip_leading_symbols(sort_name(ing.display_name))

        # 그룹: 영문 먼저(0), 그 외(한글 포함) 다음(1)
        group = 0 if is_english_start(s) else 1

        # 영문은 A-Z(대소문자 무시)
        primary = s.lower() if group == 0 else s

        # tie-breaker 포함
        return (group, primary, s)

    ingredients.sort(key=key)

    return templates.TemplateResponse(
        "recipe.html",
        {
            "request": request,
            "recipe": recipe,
            "ingredients": ingredients,
            "brand_name": BRAND_NAME,
        },
    )

@app.head("/")
def head_root():
    return Response(status_code=200)
    
@app.post("/recipe/save")
def recipe_save(
    request: Request,
    recipe_name: str = Form(""),
    unit_weight_g: float = Form(0.0),
    ingredient_id: List[int] = Form([]),
    amount_g: List[float] = Form([]),
):
    if len(ingredient_id) != len(amount_g):
        raise HTTPException(status_code=400, detail="ingredient_id and amount_g length mismatch")

    items = []
    for iid, amt in zip(ingredient_id, amount_g):
        try:
            amt_val = float(amt)
        except Exception:
            amt_val = 0.0
        if iid and amt_val and amt_val > 0:
            items.append({"ingredient_id": int(iid), "amount_g": float(amt_val)})

    request.session["recipe"] = {
        "recipe_name": recipe_name.strip(),
        "unit_weight_g": float(unit_weight_g or 0.0),
        "items": items,
    }
    return RedirectResponse(url="/result", status_code=303)


@app.post("/recipe/reset")
def recipe_reset(request: Request):
    request.session.pop("recipe", None)
    return RedirectResponse(url="/", status_code=303)


@app.get("/result", response_class=HTMLResponse)
def result_page(request: Request, db=Depends(get_db)):
    recipe = _get_recipe_session(request)
    # Hydrate items with ingredient data
    ing_map = {i.id: i for i in db.query(Ingredient).all()}
    hydrated = []
    for it in recipe.get("items", []):
        ing = ing_map.get(it["ingredient_id"])
        if ing:
            hydrated.append({"ingredient": ing, "amount_g": it["amount_g"]})

    totals = compute_totals(hydrated, unit_weight_g=recipe.get("unit_weight_g", 0.0))
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "recipe": recipe,
            "items": hydrated,
            "totals": totals,
            "brand_name": BRAND_NAME,
        },
    )


@app.get("/label.pdf")
def label_pdf(request: Request, db=Depends(get_db)):
    recipe = _get_recipe_session(request)
    ing_map = {i.id: i for i in db.query(Ingredient).all()}
    hydrated = []
    for it in recipe.get("items", []):
        ing = ing_map.get(it["ingredient_id"])
        if ing:
            hydrated.append({"ingredient": ing, "amount_g": it["amount_g"]})

    totals = compute_totals(hydrated, unit_weight_g=recipe.get("unit_weight_g", 0.0))
    pdf_bytes = build_label_pdf(
        recipe_name=recipe.get("recipe_name") or "레시피",
        unit_weight_g=float(recipe.get("unit_weight_g") or 0.0),
        totals=totals,
        items=hydrated,
        generated_at=datetime.now(),
    )

    filename = f"nutrition_label_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------- Admin ----------------

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None,
                                                           "brand_name": BRAND_NAME,})


@app.post("/admin/login")
def admin_login(request: Request, password: str = Form("")):
    if verify_admin_password(password):
        request.session["is_admin"] = True
        return RedirectResponse(url="/admin/ingredients", status_code=303)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": "비밀번호가 올바르지 않습니다.",
                                                           "brand_name": BRAND_NAME,})


@app.post("/admin/logout")
def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    return RedirectResponse(url="/", status_code=303)


@app.get(
    "/admin/ingredients",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin)]
)
def admin_ingredients(request: Request, q: str = "", db=Depends(get_db)):
    query = db.query(Ingredient)

    if q:
        like = f"%{q}%"
        query = query.filter(Ingredient.display_name.ilike(like))

    # ① DB에서 모두 가져오기
    ingredients = query.all()

    # ② 정렬 (영문 먼저 / 영문 A–Z / 한글 가나다)
    import re

    def sort_name(display_name: str) -> str:
        s = (display_name or "").strip()
        if "|" in s:
            s = s.split("|", 1)[0].strip()
        return s

    def strip_leading_symbols(s: str) -> str:
        return re.sub(r"^[^0-9A-Za-z가-힣]+", "", s)

    def is_english_start(s: str) -> bool:
        return bool(s) and s[0].isascii() and s[0].isalpha()

    def key(ing: Ingredient):
        s = strip_leading_symbols(sort_name(ing.display_name))
        group = 0 if is_english_start(s) else 1
        primary = s.lower() if group == 0 else s
        return (group, primary, s)

    ingredients.sort(key=key)

    return templates.TemplateResponse(
        "admin/ingredients.html",
        {
            "request": request,
            "ingredients": ingredients,
            "q": q,
            "brand_name": BRAND_NAME,
        },
    )


@app.get("/admin/ingredients/new", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def admin_new_ingredient_form(request: Request):
    return templates.TemplateResponse("admin/edit.html", {"request": request, "ingredient": None, "error": None,
                                                          "brand_name": BRAND_NAME,})


@app.post("/admin/ingredients/new", dependencies=[Depends(require_admin)])
def admin_new_ingredient(
    request: Request,
    name: str = Form(""),
    brand: str = Form(""),
    base_g: float = Form(100.0),
    sodium_mg_100g: float = Form(0.0),
    carbs_g_100g: float = Form(0.0),
    sugars_g_100g: float = Form(0.0),
    fiber_g_100g: float = Form(0.0),
    allulose_g_100g: float = Form(0.0),
    fat_g_100g: float = Form(0.0),
    trans_fat_g_100g: float = Form(0.0),
    sat_fat_g_100g: float = Form(0.0),
    chol_mg_100g: float = Form(0.0),
    protein_g_100g: float = Form(0.0),
    memo: str = Form(""),
    db=Depends(get_db),
):
    name = name.strip()
    brand = brand.strip()
    if not name:
        return templates.TemplateResponse("admin/edit.html", {"request": request, "ingredient": None, "error": "원재료명은 필수입니다.",
                                                              "brand_name": BRAND_NAME,})

    display_name = f"{name} | {brand}" if brand else name
    ing = Ingredient(
        display_name=display_name,
        name=name,
        brand=brand,
        base_g=float(base_g or 100.0),
        sodium_mg_100g=float(sodium_mg_100g or 0.0),
        carbs_g_100g=float(carbs_g_100g or 0.0),
        sugars_g_100g=float(sugars_g_100g or 0.0),
        fiber_g_100g=float(fiber_g_100g or 0.0),
        allulose_g_100g=float(allulose_g_100g or 0.0),
        fat_g_100g=float(fat_g_100g or 0.0),
        trans_fat_g_100g=float(trans_fat_g_100g or 0.0),
        sat_fat_g_100g=float(sat_fat_g_100g or 0.0),
        chol_mg_100g=float(chol_mg_100g or 0.0),
        protein_g_100g=float(protein_g_100g or 0.0),
        memo=memo.strip(),
    )
    db.add(ing)
    db.commit()
    return RedirectResponse(url="/admin/ingredients", status_code=303)


@app.get("/admin/ingredients/{ingredient_id}/edit", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
def admin_edit_form(ingredient_id: int, request: Request, db=Depends(get_db)):
    ing = db.query(Ingredient).get(ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse("admin/edit.html", {"request": request, "ingredient": ing, "error": None,
                                                          "brand_name": BRAND_NAME,})


@app.post("/admin/ingredients/{ingredient_id}/edit", dependencies=[Depends(require_admin)])
def admin_edit(
    ingredient_id: int,
    request: Request,
    name: str = Form(""),
    brand: str = Form(""),
    base_g: float = Form(100.0),
    sodium_mg_100g: float = Form(0.0),
    carbs_g_100g: float = Form(0.0),
    sugars_g_100g: float = Form(0.0),
    fiber_g_100g: float = Form(0.0),
    allulose_g_100g: float = Form(0.0),
    fat_g_100g: float = Form(0.0),
    trans_fat_g_100g: float = Form(0.0),
    sat_fat_g_100g: float = Form(0.0),
    chol_mg_100g: float = Form(0.0),
    protein_g_100g: float = Form(0.0),
    memo: str = Form(""),
    db=Depends(get_db),
):
    ing = db.query(Ingredient).get(ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Not found")

    name = name.strip()
    brand = brand.strip()
    if not name:
        return templates.TemplateResponse("admin/edit.html", {"request": request, "ingredient": ing, "error": "원재료명은 필수입니다.",
                                                              "brand_name": BRAND_NAME,})

    ing.name = name
    ing.brand = brand
    ing.display_name = f"{name} | {brand}" if brand else name
    ing.base_g = float(base_g or 100.0)

    ing.sodium_mg_100g = float(sodium_mg_100g or 0.0)
    ing.carbs_g_100g = float(carbs_g_100g or 0.0)
    ing.sugars_g_100g = float(sugars_g_100g or 0.0)
    ing.fiber_g_100g = float(fiber_g_100g or 0.0)
    ing.allulose_g_100g = float(allulose_g_100g or 0.0)
    ing.fat_g_100g = float(fat_g_100g or 0.0)
    ing.trans_fat_g_100g = float(trans_fat_g_100g or 0.0)
    ing.sat_fat_g_100g = float(sat_fat_g_100g or 0.0)
    ing.chol_mg_100g = float(chol_mg_100g or 0.0)
    ing.protein_g_100g = float(protein_g_100g or 0.0)
    ing.memo = memo.strip()

    db.commit()
    return RedirectResponse(url="/admin/ingredients", status_code=303)


@app.post("/admin/ingredients/{ingredient_id}/delete", dependencies=[Depends(require_admin)])
def admin_delete(ingredient_id: int, db=Depends(get_db)):
    ing = db.query(Ingredient).get(ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(ing)
    db.commit()
    return RedirectResponse(url="/admin/ingredients", status_code=303)
