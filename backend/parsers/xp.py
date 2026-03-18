import re
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import lines_by_y, find_header, col_x, parse_date, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


class XPParser(BaseBankParser):
    bank_name = "xp_extrato"
    doc_type = "checking"
    bank_code = "348"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        return "33.264.668" in text or "BANCO XP" in up or "CONTA DIGITAL XP" in up

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                lns = lines_by_y(page)
                hy, hw = find_header(lns, "Data", "Valor")
                if not hw:
                    continue
                x_val = col_x(hw, "Valor") or 400
                x_saldo = col_x(hw, "Saldo") or x_val + 80

                for y, words in lns:
                    if y <= hy:
                        continue
                    first = words[0]["text"].strip()
                    dm = re.match(r"^(\d{2}/\d{2}/\d{2})", first)
                    if not dm:
                        continue
                    dt = parse_date(dm.group(1))
                    if not dt:
                        continue

                    desc_parts, val_parts = [], []
                    for w in words:
                        t = w["text"].strip()
                        if w["x0"] >= x_saldo - 10:
                            pass  # saldo - ignorar
                        elif w["x0"] >= x_val - 15:
                            val_parts.append(t)
                        elif w["x0"] > words[0]["x1"] + 2 and t not in ("às",):
                            desc_parts.append(t)

                    val_text = "".join(val_parts)
                    if not val_text:
                        continue
                    amount = parse_br_value(val_text)
                    if amount is None:
                        continue

                    desc = clean_text(" ".join(desc_parts))
                    txs.append(Transaction(date=dt, description=desc, amount=amount, doc_type="checking"))

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        branchid = "0001"
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        # "Agência: 0001 | Conta: 11083694"
        m = re.search(r"Ag[êe]ncia[:\s]+(\d+)", text, re.IGNORECASE)
        if m:
            branchid = m.group(1)
        m = re.search(r"Conta[:\s]+(\d+)", text, re.IGNORECASE)
        if m:
            acctid = m.group(1)

        # "Saldo disponível no final do período filtrado: R$ 24,41"
        m = re.search(r"Saldo\s+dispon[ií]vel.*?R\$\s*([\d\.\-,]+)", text, re.IGNORECASE)
        if m:
            balance = parse_br_value(m.group(1)) or 0.0

        # Pegar data do periodo: "Até: 28/02/2026"
        m = re.search(r"At[ée][:\s]+(\d{2}/\d{2}/\d{4})", text)
        if m:
            balance_date = parse_date(m.group(1)) or ""

        return AccountMetadata(
            bankid=self.bank_code, branchid=branchid, acctid=acctid,
            acct_type="CHECKING", balance=balance, balance_date=balance_date
        )
