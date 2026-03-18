import re
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import lines_by_y, find_header, col_x, parse_date, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


class StoneParser(BaseBankParser):
    bank_name = "stone_extrato"
    doc_type = "checking"
    bank_code = "197"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        return "16.501.555" in text or "STONE.COM.BR" in up or "STONE INSTITUIÇÃO" in up

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []
        saved_cols = None
        SKIP_ROWS = {"Extrato de conta", "Emitido em", "Página", "Período:", "Dados da conta",
                     "Instituição", "Nome", "Documento", "Agência", "Conta"}

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                lns = lines_by_y(page)
                hy, hw = find_header(lns, "DATA", "TIPO", "VALOR")
                if hw:
                    saved_cols = {
                        "data":  col_x(hw, "DATA")   or 26,
                        "tipo":  col_x(hw, "TIPO")   or 76,
                        "desc":  col_x(hw, "DESCRI") or 121,
                        "valor": col_x(hw, "VALOR")  or 294,
                        "saldo": col_x(hw, "SALDO")  or 361,
                    }
                if not saved_cols:
                    continue
                c = saved_cols
                hy_page = hy if hw else -1

                classified = []
                for y, words in lns:
                    if y <= hy_page:
                        continue
                    row_text = " ".join(w["text"] for w in words)
                    if any(s in row_text for s in SKIP_ROWS):
                        continue
                    has_date = any(
                        w["x0"] < c["tipo"] - 5 and re.match(r"^\d{2}/\d{2}/\d{2,4}$", w["text"].strip())
                        for w in words
                    )
                    classified.append((y, words, "main" if has_date else "extra"))

                main_idxs = [i for i, (_, _, k) in enumerate(classified) if k == "main"]

                for mi, main_i in enumerate(main_idxs):
                    y_main, main_words, _ = classified[main_i]

                    pre_start = (main_idxs[mi - 1] + 1) if mi > 0 else 0
                    post_end = main_idxs[mi + 1] if mi + 1 < len(main_idxs) else len(classified)

                    pre_rows = []
                    post_rows = []
                    for j in range(pre_start, post_end):
                        if j == main_i:
                            continue
                        if classified[j][2] != "extra":
                            continue
                        ey = classified[j][0]
                        dist_to_prev_main = abs(ey - y_main)
                        next_main_y = classified[main_idxs[mi + 1]][0] if mi + 1 < len(main_idxs) else 99999
                        prev_main_y = classified[main_idxs[mi - 1]][0] if mi > 0 else -99999
                        dist_to_next = abs(ey - next_main_y)
                        dist_to_prev = abs(ey - prev_main_y)

                        if ey < y_main:
                            if dist_to_prev_main < dist_to_prev:
                                pre_rows.append(classified[j][1])
                        else:
                            if dist_to_prev_main < dist_to_next:
                                post_rows.append(classified[j][1])

                    date_word = tipo_word = val_word = None
                    desc_parts = []
                    for w in main_words:
                        wx, t = w["x0"], w["text"].strip()
                        if wx < c["tipo"] - 5:
                            if re.match(r"^\d{2}/\d{2}/\d{2,4}$", t):
                                date_word = t
                        elif wx >= c["saldo"] - 10:
                            pass
                        elif wx >= c["valor"] - 10:
                            if val_word is None:
                                val_word = t
                            else:
                                val_word += t
                        elif wx >= c["desc"] - 5:
                            desc_parts.append(t)
                        elif wx >= c["tipo"] - 5:
                            if t in ("Entrada", "Saída", "Saida"):
                                tipo_word = t
                            else:
                                desc_parts.append(t)

                    if not date_word or val_word is None:
                        continue
                    dt = parse_date(date_word)
                    amount = parse_br_value(val_word)
                    if not dt or amount is None:
                        continue

                    sign = -1 if (tipo_word or "").lower() in ("saída", "saida") else 1
                    amount = abs(amount) * sign

                    pre_text = clean_text(" ".join(w["text"].strip() for row in pre_rows for w in row))
                    post_text = clean_text(" ".join(w["text"].strip() for row in post_rows for w in row))
                    inline_desc = clean_text(" ".join(desc_parts))

                    description = pre_text or inline_desc or post_text or tipo_word or "Transação"
                    memo = " | ".join(filter(None, [
                        inline_desc if pre_text else "",
                        post_text
                    ]))

                    txs.append(Transaction(
                        date=dt, description=description[:128],
                        amount=amount, memo=clean_text(memo),
                        doc_type="checking", raw_type=tipo_word or ""
                    ))

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        branchid = "0001"
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        # "Agência Conta" / "0001 850652967"
        m = re.search(r"Ag[êe]ncia\s+Conta\s*\n\s*.*?(\d+)\s+(\d+)", text, re.IGNORECASE)
        if m:
            branchid = m.group(1)
            acctid = m.group(2)
        else:
            m = re.search(r"Ag[êe]ncia\s*\n?\s*(\d+)", text, re.IGNORECASE)
            if m:
                branchid = m.group(1)
            m = re.search(r"Conta\s*\n?\s*(\d+)", text, re.IGNORECASE)
            if m:
                acctid = m.group(1)

        # "Período: de 01/02/2026 a 28/02/2026"
        m = re.search(r"a\s+(\d{2}/\d{2}/\d{4})", text)
        if m:
            balance_date = parse_date(m.group(1)) or ""

        return AccountMetadata(
            bankid=self.bank_code, branchid=branchid, acctid=acctid,
            acct_type="CHECKING", balance=balance, balance_date=balance_date
        )
