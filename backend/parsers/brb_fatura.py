import re
from datetime import datetime
import pdfplumber

from backend.parsers.base import BaseBankParser
from backend.parsers.utils import lines_by_y, parse_date, parse_br_value, clean_text
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


class BRBFaturaParser(BaseBankParser):
    bank_name = "brb_fatura"
    doc_type = "creditcard"
    bank_code = "070"

    @classmethod
    def can_handle(cls, text: str) -> bool:
        up = text.upper()
        if "BRB" not in up and "047.033.940" not in text:
            return False
        # Markers de fatura
        return "DDAATTAA" in text or ("LANÇAMENTOS" in up and "FATURA" in up) or \
               ("VENCIMENTO" in up and "FATURA" in up)

    @staticmethod
    def _dedupe_doubled_text(text: str) -> str:
        """
        Faturas BRB frequentemente têm texto duplicado char-a-char no PDF.
        Ex: 'RR$$ 2244..448800,,0088' → 'R$ 24.480,08'
            '0088//0022//22002266' → '08/02/2026'
        Detecta e corrige tomando caracteres alternados.
        """
        if not text:
            return text
        # Verifica se o texto parece duplicado: cada char aparece 2x seguidas
        # Testa nos primeiros 10 chars (ignorando espaços)
        stripped = text.replace(" ", "")
        if len(stripped) >= 4:
            is_doubled = all(
                stripped[i] == stripped[i + 1]
                for i in range(0, min(len(stripped) - 1, 10), 2)
            )
            if is_doubled:
                return text[::2]
        return text

    @staticmethod
    def _extract_due_date_from_text(text: str) -> str | None:
        """
        Extrai data de vencimento do texto da primeira página.
        Lida com texto normal E texto duplicado char-a-char (comum em faturas BRB).

        Procura o padrão "Com vencimento em:" seguido da data, decodificando
        texto duplicado se necessário.
        """
        # Estratégia 1: regex direta para texto normal DD/MM/YYYY
        m = re.search(
            r"[Vv]encimento\s*(?:em)?[:\s]+(\d{2}/\d{2}/\d{4})", text
        )
        if m:
            return parse_date(m.group(1))

        # Estratégia 2: texto duplicado — data aparece como 0088//0022//22002266
        # Padrão: (d)(d)(d)(d)//(d)(d)//(d)(d)(d)(d)(d)(d)(d)(d)
        m = re.search(
            r"(\d)\1(\d)\2//(\d)\3(\d)\4//(\d)\5(\d)\6(\d)\7(\d)\8",
            text
        )
        if m:
            date_str = (
                f"{m.group(1)}{m.group(2)}/"
                f"{m.group(3)}{m.group(4)}/"
                f"{m.group(5)}{m.group(6)}{m.group(7)}{m.group(8)}"
            )
            return parse_date(date_str)

        # Estratégia 3: regex mais permissiva com até 200 chars entre label e data
        m = re.search(
            r"[Cc]om\s+[Vv]encimento\s+em\s*:.{0,200}?(\d{2}/\d{2}/\d{4})",
            text, re.DOTALL
        )
        if m:
            return parse_date(m.group(1))

        return None

    @staticmethod
    def _extract_due_date_by_coords(page) -> str | None:
        """
        Extrai a data de vencimento usando coordenadas dos words do pdfplumber.
        Busca no terço superior da página onde ficam os cards do header.
        """
        words = page.extract_words(keep_blank_chars=True, x_tolerance=3, y_tolerance=3)
        if not words:
            return None

        page_height = float(page.height)
        top_cutoff = page_height * 0.33

        date_re = re.compile(r"(\d{2}/\d{2}/\d{4})")

        venc_words = []
        date_words = []

        for w in words:
            if w["top"] > top_cutoff:
                continue
            txt = w["text"].strip()
            txt_lower = txt.lower()
            if "vencimento" in txt_lower:
                is_label = len(txt) < 40
                venc_words.append((w, is_label))
            m = date_re.search(txt)
            if m:
                date_words.append((w, m.group(1)))

        if not venc_words or not date_words:
            return None

        best_date = None
        best_score = float("inf")

        for vw, is_label in venc_words:
            vx0 = vw["x0"]
            vy = vw["top"]
            for dw, date_str in date_words:
                dx = abs(dw["x0"] - vx0)
                dy = dw["top"] - vy
                if dx < 100 and -5 <= dy <= 50:
                    score = dx + abs(dy)
                    if is_label:
                        score -= 1000
                    if score < best_score:
                        best_score = score
                        best_date = date_str
                elif abs(dy) < 10 and dx < 200:
                    score = dx + abs(dy) + 50
                    if is_label:
                        score -= 1000
                    if score < best_score:
                        best_score = score
                        best_date = date_str

        if best_date:
            return parse_date(best_date)
        return None

    def parse(self, pdf_path: str) -> list[Transaction]:
        txs = []

        TX_RE = re.compile(
            r"^(\d{2}/\d{2})\s+"
            r"(.+?)\s+"
            r"(R\$\s*[\d\.]+,\d{2}[+\-])$"
        )
        TIPO_RE = re.compile(
            r"(Compra a Vista|Parcela Lojista|Parc\.\s*\d+/\d+|"
            r"Est Tarifa|Tarifa|Anuidade|Saque)"
        )

        with pdfplumber.open(pdf_path) as pdf:
            p1 = pdf.pages[0]
            p1_text = p1.extract_text() or ""

            # ── Extrai data de vencimento do card "Com vencimento em:" ──
            # Estratégia 1: texto extraído (lida com texto normal e duplicado)
            due_date = self._extract_due_date_from_text(p1_text)

            # Estratégia 2: coordenadas dos words (fallback)
            if not due_date:
                due_date = self._extract_due_date_by_coords(p1)

            if not due_date:
                due_date = datetime.now().strftime("%Y-%m-%d")

            for page in pdf.pages:
                lns = lines_by_y(page)
                for _, words in lns:
                    row = " ".join(w["text"] for w in words).strip()
                    if re.search(r"([A-Z])\1{2,}", row):
                        continue
                    if any(s in row for s in ["Transações nacionais", "Transações internacionais",
                                               "Total desse cartão", "ATENÇÃO"]):
                        continue
                    m = TX_RE.match(row)
                    if not m:
                        continue
                    raw_desc = m.group(2)
                    val_text = m.group(3)
                    amount = parse_br_value(val_text)
                    if amount is None:
                        continue
                    is_expense = val_text.endswith("+")
                    amount = -abs(amount) if is_expense else abs(amount)
                    tipo_m = TIPO_RE.search(raw_desc)
                    if tipo_m:
                        desc = raw_desc[:tipo_m.start()].strip()
                        memo = raw_desc[tipo_m.start():].strip()
                    else:
                        desc = raw_desc
                        memo = ""
                    txs.append(Transaction(
                        date=due_date,
                        description=clean_text(desc or raw_desc)[:128],
                        amount=amount,
                        memo=clean_text(memo),
                        doc_type="creditcard"
                    ))

        return txs

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        acctid = "0000000"
        balance = 0.0
        balance_date = ""

        with pdfplumber.open(pdf_path) as pdf:
            p1 = pdf.pages[0]
            text = p1.extract_text() or ""

        m = re.search(r"(\d{4}\s*\*{4}\s*\*{4}\s*\d{4})", text)
        if m:
            acctid = m.group(1).replace(" ", "").replace("*", "")

        m = re.search(r"Total\s+(?:da\s+)?fatura\s*[:\s]*R\$\s*([\d\.\-,]+)", text, re.IGNORECASE)
        if not m:
            m = re.search(r"Total\s+desse\s+cart[aã]o\s*[:\s]*R\$\s*([\d\.\-,]+)", text, re.IGNORECASE)
        if m:
            balance = -(parse_br_value(m.group(1)) or 0.0)

        # Usa mesma lógica de texto (lida com texto duplicado)
        balance_date = self._extract_due_date_from_text(text) or ""

        if not balance_date:
            with pdfplumber.open(pdf_path) as pdf:
                balance_date = self._extract_due_date_by_coords(pdf.pages[0]) or ""

        return AccountMetadata(
            bankid=self.bank_code, branchid="0001", acctid=acctid,
            acct_type="CREDITCARD", balance=balance, balance_date=balance_date
        )
