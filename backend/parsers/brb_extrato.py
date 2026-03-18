import re
from datetime import datetime
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import lines_by_y, parse_date, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


class BRBExtratoParser(BaseBankParser):
    bank_name = "brb_extrato"
    doc_type = "checking"
    bank_code = "070"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        if "BRB" not in up and "047.033.940" not in text:
            return False
        # Nao e fatura
        if "DDAATTAA" in text:
            return False
        if "LANÇAMENTOS" in up and "FATURA" in up:
            return False
        return True

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []
        year_hint = datetime.now().year

        with pdfplumber.open(pdf_path) as pdf:
            all_lines = []
            for page in pdf.pages:
                all_lines.extend(lines_by_y(page, y_tol=1))

        # Inferir ano
        for _, words in all_lines:
            row = " ".join(w["text"] for w in words)
            m = re.search(r"\b(20\d{2})\b", row)
            if m:
                year_hint = int(m.group(1))
                break

        SKIP = {"Saldo", "SALDO", "Agência", "Conta Corrente", "Extrato", "Limite",
                "Poupança", "CDB", "Fundo", "Dia", "Histórico", "JANEIRO", "FEVEREIRO",
                "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO",
                "OUTUBRO", "NOVEMBRO", "DEZEMBRO", "WENDELL", "26/01"}
        DATE_RE = re.compile(r"^\d{2}/\d{2}$")
        VAL_RE  = re.compile(r"^R\$\s*[+\-−]?[\d\.]+,\d{2}$")

        tagged = []
        for y, words in all_lines:
            row_text = " ".join(w["text"] for w in words)
            if any(s in row_text for s in SKIP):
                tagged.append((y, words, "skip"))
                continue

            has_date = any(DATE_RE.match(w["text"].strip()) and w["x0"] < 30 for w in words)
            has_val  = any(VAL_RE.match(w["text"].strip()) and w["x0"] > 400 for w in words)

            if has_date or has_val:
                tagged.append((y, words, "date_val"))
            else:
                desc_words = [w["text"].strip() for w in words if w["x0"] >= 60]
                if desc_words:
                    tagged.append((y, words, "desc_only"))
                else:
                    tagged.append((y, words, "skip"))

        used = set()
        date_val_idxs = [i for i, (_, _, k) in enumerate(tagged) if k == "date_val"]

        for i in date_val_idxs:
            if i in used:
                continue
            y_main, main_words, _ = tagged[i]

            desc_words = []
            for j in range(i - 1, max(i - 4, -1), -1):
                y_j, words_j, kind_j = tagged[j]
                if kind_j == "desc_only" and abs(y_main - y_j) <= 8 and j not in used:
                    desc_words = [w["text"].strip() for w in words_j if w["x0"] >= 60]
                    used.add(j)
                    break

            used.add(i)

            date_word = val_word = None
            inline_desc = []
            for w in main_words:
                t = w["text"].strip()
                if DATE_RE.match(t) and w["x0"] < 30:
                    date_word = t
                elif VAL_RE.match(t) and w["x0"] > 400:
                    val_word = t
                elif w["x0"] >= 60:
                    inline_desc.append(t)

            if not date_word or not val_word:
                continue

            dt = parse_date(date_word, year_hint)
            if not dt:
                continue

            sign_m = re.search(r"([+\-−])", val_word)
            sign = -1 if sign_m and sign_m.group(1) in ("-", "\u2212") else 1
            num = re.search(r"[\d\.]+,\d{2}", val_word)
            if not num:
                continue
            amount = (parse_br_value(num.group(0)) or 0) * sign

            desc_parts = desc_words or inline_desc
            desc = clean_text(" ".join(desc_parts)) or "Lançamento"
            txs.append(Transaction(date=dt, description=desc[:128], amount=amount, doc_type="checking"))

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        branchid = "0001"
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        # "Agência: 047 — Conta Corrente: 047.033.940-3"
        m = re.search(r"Ag[êe]ncia[:\s]+(\d+)", text, re.IGNORECASE)
        if m:
            branchid = m.group(1)
        m = re.search(r"Conta\s+Corrente[:\s]+([\d\.\-]+)", text, re.IGNORECASE)
        if m:
            acctid = m.group(1).replace(".", "").replace("-", "")

        # "Saldo Conta Corrente R$ −196,20"
        m = re.search(r"Saldo\s+Conta\s+Corrente\s+R\$\s*([+\-−]?[\d\.,]+)", text, re.IGNORECASE)
        if m:
            balance = parse_br_value(m.group(1)) or 0.0

        # Inferir data do mes/ano no header
        m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if m:
            balance_date = parse_date(m.group(1)) or ""

        return AccountMetadata(
            bankid=self.bank_code, branchid=branchid, acctid=acctid,
            acct_type="CHECKING", balance=balance, balance_date=balance_date
        )
