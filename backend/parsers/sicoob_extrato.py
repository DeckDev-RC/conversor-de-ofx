import re
from datetime import datetime
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import parse_date, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


class SicoobExtratoParser(BaseBankParser):
    bank_name = "sicoob_extrato"
    doc_type = "checking"
    bank_code = "756"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        if "SICOOB" not in up:
            return False
        # Nao e fatura
        if "PAGAMENTO MÍNIMO" in up:
            return False
        if "VENCIMENTO" in up and "R$ 170.000" in text:
            return False
        return True

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []
        year_hint = datetime.now().year

        with pdfplumber.open(pdf_path) as pdf:
            all_text_lines = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text_lines.extend(text.split("\n"))

        for line in all_text_lines:
            m = re.search(r"PERÍODO[:\s]+\d{2}/\d{2}/(\d{4})", line)
            if m:
                year_hint = int(m.group(1))
                break

        trans_re = re.compile(r"^(\d{2}/\d{2})\s+(.+?)\s+([\d\.]+,\d{2})([DC])$")
        i = 0
        while i < len(all_text_lines):
            line = all_text_lines[i].strip()
            m = trans_re.match(line)
            if m:
                dt = parse_date(m.group(1), year_hint)
                desc = m.group(2)
                amount = parse_br_value(m.group(3) + m.group(4))
                memo_parts = []
                j = i + 1
                while j < len(all_text_lines):
                    nxt = all_text_lines[j].strip()
                    if re.match(r"^\d{2}/\d{2}\s", nxt) or not nxt or "SALDO" in nxt.upper():
                        break
                    memo_parts.append(nxt)
                    j += 1
                if not any(s in desc.upper() for s in {"SALDO ANTERIOR", "SALDO BLOQ", "SALDO FINAL"}):
                    txs.append(Transaction(
                        date=dt, description=clean_text(desc),
                        amount=amount or 0, memo=" | ".join(memo_parts),
                        doc_type="checking"
                    ))
                i = j
            else:
                i += 1

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        branchid = "0001"
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
            all_text = "\n".join((p.extract_text() or "") for p in pdf.pages)

        m = re.search(r"Ag[êe]ncia[:\s]+(\d+)", text, re.IGNORECASE)
        if m:
            branchid = m.group(1)
        m = re.search(r"Conta[:\s]+([\d\.\-]+)", text, re.IGNORECASE)
        if m:
            acctid = m.group(1).replace(".", "").replace("-", "")

        m = re.search(r"SALDO\s+FINAL\s+.*?([\d\.]+,\d{2})([DC])?", all_text, re.IGNORECASE)
        if m:
            val = parse_br_value(m.group(1) + (m.group(2) or "")) or 0.0
            balance = val

        m = re.search(r"PER[ÍI]ODO[:\s]+\d{2}/\d{2}/\d{4}\s+[aA]\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if m:
            balance_date = parse_date(m.group(1)) or ""

        return AccountMetadata(
            bankid=self.bank_code, branchid=branchid, acctid=acctid,
            acct_type="CHECKING", balance=balance, balance_date=balance_date
        )
