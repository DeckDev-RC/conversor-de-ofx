import re
from datetime import date, datetime
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import MESES, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


class SicoobFaturaParser(BaseBankParser):
    bank_name = "sicoob_fatura"
    doc_type = "creditcard"
    bank_code = "756"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        if "SICOOB" not in up:
            return False
        return "PAGAMENTO MÍNIMO" in up or ("VENCIMENTO" in up and "R$ 170.000" in text)

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []
        year_hint = datetime.now().year

        with pdfplumber.open(pdf_path) as pdf:
            all_text_lines = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text_lines.extend(text.split("\n"))

        for line in all_text_lines:
            m = re.search(r"VENCIMENTO\s+\d+\s+[A-Z]+\s+(\d{4})", line)
            if m:
                year_hint = int(m.group(1))
                break

        trans_re = re.compile(r"^(\d{2})\s+([A-Z]{3})\s+(.+?)\s+(R\$\s*[\d\.]+,\d{2})$")
        for line in all_text_lines:
            line = line.strip()
            if any(s in line for s in ["SALDO ANTERIOR", "TOTAL R$", "TOTAL DE"]):
                continue
            m = trans_re.match(line)
            if m:
                dia, mes_str, desc, val_text = m.groups()
                mes = MESES.get(mes_str.upper())
                if not mes:
                    continue
                amount = parse_br_value(val_text)
                if amount is None:
                    continue
                amount = -abs(amount)
                yr = year_hint
                if mes > 10:
                    yr = year_hint - 1
                try:
                    dt = date(yr, mes, int(dia)).isoformat()
                    txs.append(Transaction(date=dt, description=clean_text(desc), amount=amount, doc_type="creditcard"))
                except ValueError:
                    pass

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        m = re.search(r"(\d{4}\s*\*{4}\s*\*{4}\s*\d{4})", text)
        if m:
            acctid = m.group(1).replace(" ", "").replace("*", "")

        m = re.search(r"TOTAL\s+R\$\s*([\d\.]+,\d{2})", text, re.IGNORECASE)
        if m:
            balance = -(parse_br_value(m.group(1)) or 0.0)

        m = re.search(r"VENCIMENTO\s+(\d+)\s+([A-Z]+)\s+(\d{4})", text)
        if m:
            dia, mes_str, ano = m.groups()
            mes = MESES.get(mes_str.upper())
            if mes:
                try:
                    balance_date = date(int(ano), mes, int(dia)).isoformat()
                except ValueError:
                    pass

        return AccountMetadata(
            bankid=self.bank_code, branchid="0001", acctid=acctid,
            acct_type="CREDITCARD", balance=balance, balance_date=balance_date
        )