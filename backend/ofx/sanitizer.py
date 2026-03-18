import re
from backend.ofx.constants import DEFAULT_TIME, TIMEZONE


def sanitize_ofx_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('&', 'e')
    text = text.replace('<', '(')
    text = text.replace('>', ')')
    return text[:255]


def format_ofx_date(iso_date: str) -> str:
    return iso_date.replace('-', '') + DEFAULT_TIME + TIMEZONE


def format_ofx_amount(amount: float) -> str:
    return f"{amount:.2f}"
