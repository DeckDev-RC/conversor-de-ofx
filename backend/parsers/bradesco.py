import re
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import lines_by_y, find_header, col_x, parse_date, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


BRADESCO_SKIP = {"SALDO ANTERIOR", "SALDO INVEST", "SALDO APLIC"}


class BradescoParser(BaseBankParser):
    bank_name = "bradesco_extrato"
    doc_type = "checking"
    bank_code = "237"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        return "60.746.948" in text or "BRADESCO" in up or "NET EMPRESA" in up or \
               "BANCO TRIANGULO" in up or \
               "CRÉDITO (R$)" in text or "DÉBITO (R$)" in text or "Crédito (R$)" in text

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []
        saved_cols = None
        SKIP_TEXT = {"Folha", "Extrato Mensal", "Data da opera", "Os dados acima",
                     "Nome do usu", "Últimos Lançamentos", "SALDO INVEST", "Saldos Invest"}
        last_date = None

        def process_page_rows(rows):
            nonlocal last_date
            val_idxs = [i for i, r in enumerate(rows) if r["kind"] == "val"]
            if not val_idxs:
                return []

            def nearest_val_idx(j):
                y_j = rows[j]["y"]
                best_i, best_dist = None, 99999
                for i in val_idxs:
                    d = abs(rows[i]["y"] - y_j)
                    if d < best_dist:
                        best_dist = d
                        best_i = i
                return best_i

            text_assignment = {j: nearest_val_idx(j)
                               for j, r in enumerate(rows) if r["kind"] == "text"}

            page_txs = []
            for vi in val_idxs:
                vrow = rows[vi]
                dt = parse_date(vrow["date"]) if vrow["date"] else last_date
                if vrow["date"]:
                    last_date = dt
                if not dt or vrow["val"] is None:
                    continue

                assigned = [j for j, vi2 in text_assignment.items() if vi2 == vi]
                pre_lanc  = [rows[j]["lanc"] for j in assigned if rows[j]["y"] < vrow["y"]]
                post_lanc = [rows[j]["lanc"] for j in assigned if rows[j]["y"] > vrow["y"]]

                tipo   = clean_text(" ".join(w for r in pre_lanc  for w in r))
                inline = clean_text(" ".join(vrow["lanc"]))
                memo   = clean_text(" ".join(w for r in post_lanc for w in r))

                desc = tipo or inline or "Lançamento"
                if any(s in desc.upper() for s in BRADESCO_SKIP):
                    continue

                full_memo = " | ".join(filter(None, [inline if tipo else "", memo]))
                page_txs.append(Transaction(
                    date=dt, description=desc[:128],
                    amount=vrow["val"], memo=clean_text(full_memo),
                    doc_type="checking"
                ))
            return page_txs

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                lns = lines_by_y(page)
                hy, hw = find_header(lns, "Data", "Dcto")
                if not hw:
                    hy, hw = find_header(lns, "Data", "dito")
                if hw:
                    saved_cols = {
                        "data":    col_x(hw, "Data")  or 41,
                        "lanc":    col_x(hw, "Lan")   or 101,
                        "credito": col_x(hw, "dit")   or 338,
                        "debito":  col_x(hw, "bit")   or 428,
                        "saldo":   col_x(hw, "Saldo") or 519,
                    }
                    hy_page = hy
                else:
                    hy_page = -1

                if not saved_cols:
                    continue

                c = saved_cols
                page_rows = []

                for y, words in lns:
                    if y <= hy_page:
                        continue
                    row_text = " ".join(w["text"] for w in words)
                    if any(s in row_text for s in SKIP_TEXT):
                        continue
                    if re.match(r"^Total\s", row_text):
                        continue

                    date_word = credit_word = debit_word = None
                    lanc_words = []

                    for w in words:
                        wx, t = w["x0"], w["text"].strip()
                        if wx < c["lanc"] - 5:
                            if re.match(r"^\d{2}/\d{2}/\d{4}$", t):
                                date_word = t
                        elif wx >= c["saldo"] - 20:
                            pass
                        elif wx >= c["debito"] - 20 and wx < c["saldo"] - 20:
                            debit_word = t
                        elif wx >= c["credito"] - 20 and wx < c["debito"] - 20:
                            credit_word = t
                        elif wx >= c["lanc"] - 5:
                            lanc_words.append(t)

                    line_val = None
                    if credit_word:
                        v = parse_br_value(credit_word)
                        if v is not None:
                            line_val = abs(v)
                    if debit_word:
                        v = parse_br_value(debit_word)
                        if v is not None:
                            line_val = -abs(v)

                    if date_word or line_val is not None:
                        kind = "val"
                    elif lanc_words:
                        kind = "text"
                    else:
                        continue

                    page_rows.append({"y": y, "kind": kind, "date": date_word,
                                       "val": line_val, "lanc": lanc_words})

                txs.extend(process_page_rows(page_rows))

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        branchid = "0001"
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        m = re.search(r"Ag[êe]ncia[:\s]+(\d+)", text, re.IGNORECASE)
        if m:
            branchid = m.group(1)
        m = re.search(r"Conta[:\s]+([\d\.\-]+)", text, re.IGNORECASE)
        if m:
            acctid = m.group(1).replace(".", "").replace("-", "")

        m = re.search(r"Saldo\s+(?:em\s+)?(?:conta\s+)?.*?R\$\s*([\-]?[\d\.]+,\d{2})", text, re.IGNORECASE)
        if m:
            balance = parse_br_value(m.group(1)) or 0.0

        m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if m:
            balance_date = parse_date(m.group(1)) or ""

        return AccountMetadata(
            bankid=self.bank_code, branchid=branchid, acctid=acctid,
            acct_type="CHECKING", balance=balance, balance_date=balance_date
        )