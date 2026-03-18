import hashlib
from backend.ofx.constants import OFX_HEADER
from backend.ofx.sanitizer import sanitize_ofx_text, format_ofx_date, format_ofx_amount


def _make_fitid(date: str, amount: float, description: str) -> str:
    raw = f"{date}|{amount}|{description}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16].upper()


def generate_ofx(parse_result: dict) -> str:
    metadata = parse_result.get("metadata", {})
    transactions = parse_result.get("transactions", [])
    acct_type = metadata.get("acct_type", "CHECKING")

    transactions = sorted(transactions, key=lambda t: (t["date"], t.get("fitid", "")))

    if acct_type == "CREDITCARD":
        return _generate_creditcard_ofx(transactions, metadata)
    return _generate_checking_ofx(transactions, metadata)


def _generate_checking_ofx(transactions: list[dict], meta: dict) -> str:
    lines = [OFX_HEADER]
    lines.append("<OFX>")
    lines.append("<SIGNONMSGSRSV1>")
    lines.append("<SONRS>")
    lines.append("<STATUS>")
    lines.append("<CODE>0")
    lines.append("<SEVERITY>INFO")
    lines.append("</STATUS>")
    lines.append("<DTSERVER>" + _now_ofx())
    lines.append("<LANGUAGE>POR")
    lines.append("</SONRS>")
    lines.append("</SIGNONMSGSRSV1>")
    lines.append("<BANKMSGSRSV1>")
    lines.append("<STMTTRNRS>")
    lines.append("<TRNUID>1")
    lines.append("<STATUS>")
    lines.append("<CODE>0")
    lines.append("<SEVERITY>INFO")
    lines.append("</STATUS>")
    lines.append("<STMTRS>")
    lines.append("<CURDEF>BRL")
    lines.append("<BANKACCTFROM>")
    lines.append("<BANKID>" + meta.get("bankid", "000"))
    lines.append("<BRANCHID>" + meta.get("branchid", "0001"))
    lines.append("<ACCTID>" + meta.get("acctid", "0000000"))
    lines.append("<ACCTTYPE>CHECKING")
    lines.append("</BANKACCTFROM>")

    dtstart, dtend = _date_range(transactions)
    lines.append("<BANKTRANLIST>")
    lines.append("<DTSTART>" + dtstart)
    lines.append("<DTEND>" + dtend)

    for tx in transactions:
        lines.extend(_transaction_block(tx))

    lines.append("</BANKTRANLIST>")

    balance = meta.get("balance", 0.0)
    balance_date = meta.get("balance_date", "")
    lines.append("<LEDGERBAL>")
    lines.append("<BALAMT>" + format_ofx_amount(balance))
    lines.append("<DTASOF>" + (format_ofx_date(balance_date) if balance_date else dtend))
    lines.append("</LEDGERBAL>")

    lines.append("</STMTRS>")
    lines.append("</STMTTRNRS>")
    lines.append("</BANKMSGSRSV1>")
    lines.append("</OFX>")

    return "\r\n".join(lines) + "\r\n"


def _generate_creditcard_ofx(transactions: list[dict], meta: dict) -> str:
    lines = [OFX_HEADER]
    lines.append("<OFX>")
    lines.append("<SIGNONMSGSRSV1>")
    lines.append("<SONRS>")
    lines.append("<STATUS>")
    lines.append("<CODE>0")
    lines.append("<SEVERITY>INFO")
    lines.append("</STATUS>")
    lines.append("<DTSERVER>" + _now_ofx())
    lines.append("<LANGUAGE>POR")
    lines.append("</SONRS>")
    lines.append("</SIGNONMSGSRSV1>")
    lines.append("<CREDITCARDMSGSRSV1>")
    lines.append("<CCSTMTTRNRS>")
    lines.append("<TRNUID>1")
    lines.append("<STATUS>")
    lines.append("<CODE>0")
    lines.append("<SEVERITY>INFO")
    lines.append("</STATUS>")
    lines.append("<CCSTMTRS>")
    lines.append("<CURDEF>BRL")
    lines.append("<CCACCTFROM>")
    lines.append("<ACCTID>" + meta.get("acctid", "0000000"))
    lines.append("</CCACCTFROM>")

    dtstart, dtend = _date_range(transactions)
    lines.append("<BANKTRANLIST>")
    lines.append("<DTSTART>" + dtstart)
    lines.append("<DTEND>" + dtend)

    for tx in transactions:
        lines.extend(_transaction_block(tx))

    lines.append("</BANKTRANLIST>")

    balance = meta.get("balance", 0.0)
    balance_date = meta.get("balance_date", "")
    lines.append("<LEDGERBAL>")
    lines.append("<BALAMT>" + format_ofx_amount(balance))
    lines.append("<DTASOF>" + (format_ofx_date(balance_date) if balance_date else dtend))
    lines.append("</LEDGERBAL>")

    lines.append("</CCSTMTRS>")
    lines.append("</CCSTMTTRNRS>")
    lines.append("</CREDITCARDMSGSRSV1>")
    lines.append("</OFX>")

    return "\r\n".join(lines) + "\r\n"


def _transaction_block(tx: dict) -> list[str]:
    amount = tx.get("amount", 0)
    trntype = "CREDIT" if amount > 0 else "DEBIT"
    dtposted = format_ofx_date(tx.get("date", ""))
    fitid = _make_fitid(tx.get("date", ""), amount, tx.get("description", ""))
    name = sanitize_ofx_text(tx.get("description", ""))

    return [
        "<STMTTRN>",
        "<TRNTYPE>" + trntype,
        "<DTPOSTED>" + dtposted,
        "<TRNAMT>" + format_ofx_amount(amount),
        "<FITID>" + fitid,
        "<NAME>" + name,
        "</STMTTRN>",
    ]


def _date_range(transactions: list[dict]) -> tuple[str, str]:
    if not transactions:
        from backend.ofx.sanitizer import format_ofx_date as _fmt
        return _fmt("2000-01-01"), _fmt("2000-01-01")
    dates = [tx["date"] for tx in transactions if tx.get("date")]
    if not dates:
        from backend.ofx.sanitizer import format_ofx_date as _fmt
        return _fmt("2000-01-01"), _fmt("2000-01-01")
    return format_ofx_date(min(dates)), format_ofx_date(max(dates))


def _now_ofx() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d%H%M%S") + "[-3:GMT]"
