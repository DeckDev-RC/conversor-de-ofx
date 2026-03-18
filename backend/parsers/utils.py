import re
from datetime import datetime, date
from typing import Optional
from collections import defaultdict


MESES = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}


def parse_br_value(text: str) -> Optional[float]:
    """'R$ -1.234,56' / '1.234,56D' / '1.234,56+' -> float ou None."""
    if not text:
        return None
    t = text.replace("R$", "").replace("\xa0", "").replace(" ", "").strip()
    # sufixo D/C
    dc = None
    if t and t[-1] in "DCdc":
        dc = t[-1].upper()
        t = t[:-1]
    # sinal sufixo +/-
    sign = 1
    if t.endswith("+"):
        sign = 1
        t = t[:-1]
    elif t.endswith("-"):
        sign = -1
        t = t[:-1]
    # sinal prefixo
    if t.startswith("-"):
        sign = -1
        t = t[1:]
    elif t.startswith("+"):
        sign = 1
        t = t[1:]
    # remover unicode minus
    t = t.replace("\u2212", "").replace("\u2013", "")
    t = t.replace(".", "").replace(",", ".")
    try:
        v = float(t) * sign
        if dc == "D":
            v = -abs(v)
        elif dc == "C":
            v = abs(v)
        return v
    except ValueError:
        return None


def clean_text(text: str) -> str:
    """Remove espacos duplos e normaliza unicode."""
    return re.sub(r"\s+", " ", text).strip()


def lines_by_y(page, x_tol=3, y_tol=3):
    """Retorna lista de (y, [words]) agrupados por linha."""
    words = page.extract_words(keep_blank_chars=True, x_tolerance=x_tol, y_tolerance=y_tol)
    by_y = defaultdict(list)
    for w in words:
        by_y[round(w["top"])].append(w)
    return [(y, sorted(v, key=lambda w: w["x0"])) for y, v in sorted(by_y.items())]


def find_header(lines, *keywords):
    """Retorna (y, words) da linha que contenha TODAS as keywords (case-insensitive)."""
    kw_up = [k.upper() for k in keywords]
    for y, words in lines:
        row = " ".join(w["text"] for w in words).upper()
        if all(k in row for k in kw_up):
            return y, words
    return None, None


def col_x(words, keyword) -> Optional[float]:
    """Retorna x0 da word que contem keyword."""
    for w in words:
        if keyword.upper() in w["text"].upper():
            return w["x0"]
    return None


def parse_date(s: str, year_hint: int = None) -> Optional[str]:
    """
    Tenta parsear varios formatos de data brasileiros.
    Retorna "YYYY-MM-DD" ou None.
    """
    s = s.strip()
    yr = year_hint or datetime.now().year

    # Remove horario se presente: "11/02/26 as 07:06:35" -> "11/02/26"
    s = re.split(r"\s+às\s+", s)[0].strip()

    # DD/MM/YYYY
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        try:
            return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
        except ValueError:
            pass

    # DD/MM/YY
    m = re.match(r"^(\d{2})/(\d{2})/(\d{2})$", s)
    if m:
        d, mo, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(2000 + yy, mo, d).isoformat()
        except ValueError:
            pass

    # DD/MM
    m = re.match(r"^(\d{2})/(\d{2})$", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        try:
            return date(yr, mo, d).isoformat()
        except ValueError:
            pass

    return None
