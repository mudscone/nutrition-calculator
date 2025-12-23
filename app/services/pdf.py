from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


# Register a Korean TTF font bundled with the project.
# Put the font file here:
#   app/assets/fonts/NotoSansKR-Regular.ttf
_FONT_NAME = "NotoSansKR"
_FONT_REGISTERED = False


def _register_font() -> bool:
    """
    Try to register Korean font once.
    Returns True if registered, False otherwise (fallback will be used).
    """
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return True

    # This file is located at: app/services/pdf.py
    # We want: app/assets/fonts/NotoSansKR-Regular.ttf
    font_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NotoSansKR-Regular.ttf")
    )

    if not os.path.exists(font_path):
        return False

    try:
        pdfmetrics.registerFont(TTFont(_FONT_NAME, font_path))
        _FONT_REGISTERED = True
        return True
    except Exception:
        return False


def _set_font(c: canvas.Canvas, size: int, bold: bool = False) -> None:
    """
    Set a usable font. If Korean font is available, use it; otherwise fallback to Helvetica.
    Note: Helvetica cannot render Korean.
    """
    if _register_font():
        # NotoSansKR doesn't have a separate built-in "bold" file here.
        # If you want bold, add NotoSansKR-Bold.ttf and register separately.
        c.setFont(_FONT_NAME, size)
    else:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)


def build_label_pdf(
    recipe_name: str,
    unit_weight_g: float,
    totals: Dict[str, Any],
    items: List[Dict[str, Any]],
    generated_at: datetime,
) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    x = 20 * mm
    y = height - 20 * mm

    _set_font(c, 16, bold=True)
    c.drawString(x, y, "영양성분표 (Nutrition Facts)")
    y -= 10 * mm

    _set_font(c, 11, bold=False)
    c.drawString(x, y, f"레시피명: {recipe_name}")
    y -= 6 * mm
    c.drawString(x, y, f"1개 무게: {unit_weight_g:.1f} g")
    y -= 6 * mm
    c.drawString(x, y, f"산출일: {generated_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 10 * mm

    # Table header
    _set_font(c, 11, bold=True)
    c.drawString(x, y, "항목")
    c.drawString(x + 70 * mm, y, "1개 기준")
    c.drawString(x + 110 * mm, y, "100g 기준")
    y -= 4 * mm
    c.line(x, y, width - 20 * mm, y)
    y -= 6 * mm

    _set_font(c, 11, bold=False)
    for key, label, unit in totals["order"]:
        v_unit = totals["per_unit"].get(key, 0)
        v_100 = totals["per_100g"].get(key, 0)
        c.drawString(x, y, label)
        c.drawRightString(x + 98 * mm, y, f"{v_unit} {unit}")
        c.drawRightString(x + 138 * mm, y, f"{v_100} {unit}")
        y -= 6 * mm

        if y < 60 * mm:
            c.showPage()
            y = height - 20 * mm
            _set_font(c, 11, bold=False)

    y -= 6 * mm
    _set_font(c, 11, bold=True)
    c.drawString(x, y, "레시피 구성 (원재료 | 사용량 g)")
    y -= 4 * mm
    c.line(x, y, width - 20 * mm, y)
    y -= 6 * mm

    _set_font(c, 10, bold=False)
    for it in items:
        ing = it["ingredient"]
        amt = it["amount_g"]
        line = f"- {ing.display_name}  |  {amt:.2f} g"
        c.drawString(x, y, line)
        y -= 5 * mm

        if y < 20 * mm:
            c.showPage()
            y = height - 20 * mm
            _set_font(c, 10, bold=False)

    c.showPage()
    c.save()
    return buf.getvalue()

