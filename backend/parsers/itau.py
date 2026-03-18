import re
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import lines_by_y, find_header, col_x, parse_date, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


ITAU_SKIP = {"SALDO ANTERIOR", "SALDO TOTAL", "SALDO MOVIMENTA", "SALDO EM CONTA",
             "SALDO APLIC", "SALDO TOTAL DISPONÍVEL", "SALDO MOVIMENTAÇÃO"}


def _is_itau_skip(text: str) -> bool:
    up = text.upper()
    return any(s in up for s in ITAU_SKIP)


class ItauParser(BaseBankParser):
    bank_name = "itau_extrato"
    doc_type = "checking"
    bank_code = "341"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        return "60.701.190" in text or "ITAÚ" in text or "ITAU UNIBANCO" in up or "SISPAG" in up

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []
        saved_cols = None

        def get_y(words):
            return round(words[0]["top"]) if words else 0

        def process_page(page_lines, c):
            mains  = [(words, True)  for words, has_date, has_val in page_lines if has_date]
            extras = [(words, False) for words, has_date, has_val in page_lines if not has_date]

            extra_assignment = {}
            for ei, (ewords, _) in enumerate(extras):
                ey = get_y(ewords)
                best_mi, best_dist = None, 99999
                for mi2, (mwords, _) in enumerate(mains):
                    d = abs(ey - get_y(mwords))
                    if d < best_dist:
                        best_dist = d
                        best_mi = mi2
                extra_assignment[ei] = best_mi

            page_txs = []
            for mi2, (mwords, _) in enumerate(mains):
                my = get_y(mwords)
                pre_rows  = [ewords for ei, (ewords, _) in enumerate(extras)
                             if extra_assignment[ei] == mi2 and get_y(ewords) < my]
                post_rows = [ewords for ei, (ewords, _) in enumerate(extras)
                             if extra_assignment[ei] == mi2 and get_y(ewords) > my]

                date_word = val_word = None
                lanc_w, razao_w = [], []
                for w in mwords:
                    wx, t = w["x0"], w["text"].strip()
                    if wx < c["lanc"] - 5 and re.match(r"^\d{2}/\d{2}/\d{4}$", t):
                        date_word = t
                    elif wx >= c["saldo"] - 10:
                        pass
                    elif wx >= c["valor"] - 15:
                        if val_word is None:
                            val_word = t
                    elif c.get("razao") and wx >= c["razao"] - 10 and wx < c["valor"] - 20:
                        razao_w.append(t)
                    elif wx >= c["lanc"] - 5:
                        lanc_w.append(t)

                if not date_word or val_word is None:
                    continue
                dt = parse_date(date_word)
                amount = parse_br_value(val_word)
                if not dt or amount is None:
                    continue

                pre_lanc, pre_razao = [], []
                for row in pre_rows:
                    for w in row:
                        wx, t = w["x0"], w["text"].strip()
                        if not t:
                            continue
                        if c.get("razao") and wx >= c["razao"] - 10 and wx < c["valor"] - 20:
                            pre_razao.append(t)
                        elif wx >= c["lanc"] - 5 and wx < c["valor"] - 20:
                            pre_lanc.append(t)

                post_parts = []
                for row in post_rows:
                    for w in row:
                        wx, t = w["x0"], w["text"].strip()
                        if t and wx >= c["lanc"] - 5 and wx < c["saldo"] - 10:
                            post_parts.append(t)

                desc_parts = pre_lanc + pre_razao + lanc_w + razao_w
                desc = clean_text(" ".join(desc_parts))
                memo = clean_text(" ".join(post_parts))

                if _is_itau_skip(desc):
                    continue

                txs.append(Transaction(
                    date=dt, description=desc[:128],
                    amount=amount, memo=memo,
                    doc_type="checking"
                ))
            return page_txs

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                lns = lines_by_y(page)
                hy, hw = find_header(lns, "Data", "Valor")
                if hw:
                    saved_cols = {
                        "data":  col_x(hw, "Data")  or 35,
                        "lanc":  col_x(hw, "Lan")   or 90,
                        "razao": col_x(hw, "Raz"),
                        "valor": col_x(hw, "Valor") or 460,
                        "saldo": col_x(hw, "Saldo") or 515,
                    }
                    hy_page = hy
                else:
                    hy_page = -1

                if not saved_cols:
                    continue

                c = saved_cols
                page_lines = []
                for y, words in lns:
                    if y <= hy_page:
                        continue
                    has_date = any(
                        w["x0"] < c["lanc"] - 5 and re.match(r"^\d{2}/\d{2}/\d{4}$", w["text"].strip())
                        for w in words
                    )
                    has_val = any(w["x0"] >= c["valor"] - 15 and w["x0"] < c["saldo"] - 10 for w in words)
                    page_lines.append((words, has_date, has_val))

                txs.extend(process_page(page_lines, c))

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        branchid = "0001"
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        # "Agência 0656 Conta 0099729-3"
        m = re.search(r"Ag[êe]ncia\s+(\d+)", text, re.IGNORECASE)
        if m:
            branchid = m.group(1)
        m = re.search(r"Conta\s+([\d\-]+)", text, re.IGNORECASE)
        if m:
            acctid = m.group(1).replace("-", "")

        # Saldo total na segunda linha: "-R$ 44.928,18"
        m = re.search(r"Saldo\s+total.*?\n.*?([\-]?R\$\s*[\d\.\-,]+)", text, re.IGNORECASE)
        if m:
            balance = parse_br_value(m.group(1)) or 0.0

        # "até 25/02/2026"
        m = re.search(r"at[ée]\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if m:
            balance_date = parse_date(m.group(1)) or ""

        return AccountMetadata(
            bankid=self.bank_code, branchid=branchid, acctid=acctid,
            acct_type="CHECKING", balance=balance, balance_date=balance_date
        )
