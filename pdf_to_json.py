"""
pdf_to_json.py
==============
Parser universal PDF → JSON para extratos e faturas bancárias brasileiras.

Arquitetura:
  BasePDFParser  →  detecta banco  →  BankPlugin (resolve sign + date)
                                     ↓
                              List[Transaction]  →  JSON

Bancos suportados:
  - XP (extrato)
  - Itaú (extrato)
  - Stone (extrato)
  - BRB (extrato + fatura)
  - Sicoob (extrato + fatura)
  - Bradesco (extrato)
"""

import re
import json
import uuid
import unicodedata
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict
from pathlib import Path
import pdfplumber


# ─────────────────────────────────────────────
# Modelo de saída (contrato)
# ─────────────────────────────────────────────

@dataclass
class Transaction:
    date: str          # ISO 8601 "YYYY-MM-DD"
    description: str   # texto limpo, sem duplo espaço
    amount: float      # negativo = débito, positivo = crédito
    memo: str = ""     # info complementar (CNPJ, contraparte, doc)
    doc_type: str = "checking"   # "checking" | "creditcard"
    raw_type: str = ""  # tipo original do banco (ex: "Entrada", "D", "C")
    fitid: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self):
        return asdict(self)


# ─────────────────────────────────────────────
# Utilitários comuns
# ─────────────────────────────────────────────

def parse_br_value(text: str) -> Optional[float]:
    """'R$ -1.234,56' / '1.234,56D' / '1.234,56+' → float ou None."""
    if not text:
        return None
    t = text.replace("R$", "").replace("\xa0", "").replace(" ", "").strip()
    # sufixo D/C
    dc = None
    if t and t[-1] in "DCdc":
        dc = t[-1].upper()
        t = t[:-1]
    # sinal sufixo +/-
    sign = 1
    if t.endswith("+"):
        sign = 1
        t = t[:-1]
    elif t.endswith("-"):
        sign = -1
        t = t[:-1]
    # sinal prefixo
    if t.startswith("-"):
        sign = -1
        t = t[1:]
    elif t.startswith("+"):
        sign = 1
        t = t[1:]
    # remover −  (unicode minus)
    t = t.replace("−", "").replace("–", "")
    t = t.replace(".", "").replace(",", ".")
    try:
        v = float(t) * sign
        if dc == "D":
            v = -abs(v)
        elif dc == "C":
            v = abs(v)
        return v
    except ValueError:
        return None


def clean_text(text: str) -> str:
    """Remove espaços duplos e normaliza unicode."""
    return re.sub(r"\s+", " ", text).strip()


def lines_by_y(page, x_tol=3, y_tol=3):
    """Retorna lista de (y, [words]) agrupados por linha."""
    words = page.extract_words(keep_blank_chars=True, x_tolerance=x_tol, y_tolerance=y_tol)
    by_y = defaultdict(list)
    for w in words:
        by_y[round(w["top"])].append(w)
    return [(y, sorted(v, key=lambda w: w["x0"])) for y, v in sorted(by_y.items())]


def find_header(lines, *keywords):
    """Retorna (y, words) da linha que contenha TODAS as keywords (case-insensitive)."""
    kw_up = [k.upper() for k in keywords]
    for y, words in lines:
        row = " ".join(w["text"] for w in words).upper()
        if all(k in row for k in kw_up):
            return y, words
    return None, None


def col_x(words, keyword) -> Optional[float]:
    """Retorna x0 da word que contém keyword."""
    for w in words:
        if keyword.upper() in w["text"].upper():
            return w["x0"]
    return None


def parse_date(s: str, year_hint: int = None) -> Optional[str]:
    """
    Tenta parsear vários formatos de data brasileiros.
    Retorna "YYYY-MM-DD" ou None.
    """
    s = s.strip()
    yr = year_hint or datetime.now().year

    # Remove horário se presente: "11/02/26 às 07:06:35" → "11/02/26"
    s = re.split(r"\s+às\s+", s)[0].strip()

    patterns = [
        (r"(\d{2})/(\d{2})/(\d{4})", "%d/%m/%Y"),
        (r"(\d{2})/(\d{2})/(\d{2})$", None),   # DD/MM/YY
        (r"(\d{2})/(\d{2})$", None),             # DD/MM (precisa year_hint)
    ]

    # DD/MM/YYYY
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        try:
            return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
        except ValueError:
            pass

    # DD/MM/YY
    m = re.match(r"^(\d{2})/(\d{2})/(\d{2})$", s)
    if m:
        d, mo, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(2000 + yy, mo, d).isoformat()

    # DD/MM
    m = re.match(r"^(\d{2})/(\d{2})$", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        try:
            return date(yr, mo, d).isoformat()
        except ValueError:
            pass

    return None


# ─────────────────────────────────────────────
# Parser XP — extrato
# ─────────────────────────────────────────────

def parse_xp(pdf_path: str) -> list[Transaction]:
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
                # data contém "DD/MM/YY às HH:MM:SS"
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
                        pass  # saldo — ignorar
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


# ─────────────────────────────────────────────
# Parser Itaú — extrato (multi-linha)
# ─────────────────────────────────────────────

ITAU_SKIP = {"SALDO ANTERIOR", "SALDO TOTAL", "SALDO MOVIMENTA", "SALDO EM CONTA",
             "SALDO APLIC", "SALDO TOTAL DISPONÍVEL", "SALDO MOVIMENTAÇÃO"}

def _is_itau_skip(text: str) -> bool:
    up = text.upper()
    return any(s in up for s in ITAU_SKIP)


def parse_itau(pdf_path: str) -> list[Transaction]:
    """
    Itaú Empresas — layout multi-linha com descrição PRÉ-data.
    Padrão:
      y=258  RECEBIMENTO REDE MAST   REDECARD INSTITUICAO DE    ← pré (sem data)
      y=264  02/02/2026  CNPJ  21.358,31                        ← main (data+valor)
      y=269  CD0045085048  PAGAMENTO S.A.                        ← pós (memo)

    Processado página por página para evitar confusão de Y entre páginas.
    Extras associadas à main mais próxima por gap de Y.
    Pre-rows → descrição, post-rows → memo.
    """
    txs = []
    saved_cols = None

    def get_y(words):
        return round(words[0]["top"]) if words else 0

    def process_page(page_lines, c):
        """Agrupa linhas de uma página e emite transações."""
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

            # Desc = pré (nome da operação) + inline (lanc da main)
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

            # Memo = pós (complemento/CNPJ)
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

            txs_item = Transaction(
                date=dt, description=desc[:128],
                amount=amount, memo=memo,
                doc_type="checking"
            )
            page_txs.append(txs_item)
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

# ─────────────────────────────────────────────
# Parser Stone — extrato (multi-linha, TIPO resolve sinal)
# ─────────────────────────────────────────────

def parse_stone(pdf_path: str) -> list[Transaction]:
    """
    Stone — layout multi-linha com contraparte ANTES ou DEPOIS da linha principal.
    Padrão:
      [contraparte multi-linha]   ← sem data, sem valor, col desc
      DATE TIPO DESC? VALOR       ← linha principal
      [tipo/canal]                ← ex "Pix | Maquininha"

    Estratégia: coletar todas as linhas da página em ordem, depois agrupar
    por proximidade: linhas sem data pertencem à data mais próxima.
    """
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

            # Primeiro passo: classificar cada linha
            classified = []  # (y, words, kind) onde kind = "main" | "extra"
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

            # Segundo passo: agrupar extras à main mais próxima
            # Cada main coleta extras anteriores (até a main anterior) e posteriores (até a próxima main)
            main_idxs = [i for i, (_, _, k) in enumerate(classified) if k == "main"]

            for mi, main_i in enumerate(main_idxs):
                y_main, main_words, _ = classified[main_i]

                pre_start = (main_idxs[mi - 1] + 1) if mi > 0 else 0
                post_end = main_idxs[mi + 1] if mi + 1 < len(main_idxs) else len(classified)

                # Para cada extra, associar à main mais próxima por gap em Y
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
                        # extra está acima da main → é pré se mais próximo desta do que da anterior
                        if dist_to_prev_main < dist_to_prev:
                            pre_rows.append(classified[j][1])
                    else:
                        # extra está abaixo da main → é pós se mais próximo desta do que da próxima
                        if dist_to_prev_main < dist_to_next:
                            post_rows.append(classified[j][1])

                # Parsear linha principal
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

                # Montar descrição: extras pré (contraparte) + desc inline + extras pós (canal)
                pre_text = clean_text(" ".join(w["text"].strip() for row in pre_rows for w in row))
                post_text = clean_text(" ".join(w["text"].strip() for row in post_rows for w in row))
                inline_desc = clean_text(" ".join(desc_parts))

                # Prioridade: contraparte pré > inline > canal pós
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


# ─────────────────────────────────────────────
# Parser BRB — extrato
# ─────────────────────────────────────────────

def parse_brb_extrato(pdf_path: str) -> list[Transaction]:
    """
    BRB extrato — descrição e data/valor em linhas adjacentes (Y diferindo até 8pt).
    Padrão:
      y=228 [desc x=77]              ← descrição
      y=229 [data x=10] [val x=540]  ← data + valor  (gap=1pt)
    ou:
      y=250 [desc x=77]
      y=256 [data x=10] [val x=540]  ← gap=6pt
    ou tudo numa linha só (gap=0).
    """
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

    # Marcar cada linha como: "date_val", "desc_only", ou "skip"
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

    # Para cada linha date_val, buscar desc_only adjacente (gap ≤ 8pt)
    used = set()
    date_val_idxs = [i for i, (_, _, k) in enumerate(tagged) if k == "date_val"]

    for i in date_val_idxs:
        if i in used:
            continue
        y_main, main_words, _ = tagged[i]

        # Buscar desc_only antes (gap ≤ 8)
        desc_words = []
        for j in range(i - 1, max(i - 4, -1), -1):
            y_j, words_j, kind_j = tagged[j]
            if kind_j == "desc_only" and abs(y_main - y_j) <= 8 and j not in used:
                desc_words = [w["text"].strip() for w in words_j if w["x0"] >= 60]
                used.add(j)
                break

        used.add(i)

        # Extrair data, sinal e valor da linha principal
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
        sign = -1 if sign_m and sign_m.group(1) in ("-", "−") else 1
        num = re.search(r"[\d\.]+,\d{2}", val_word)
        if not num:
            continue
        amount = (parse_br_value(num.group(0)) or 0) * sign

        # Descrição: pré (desc_only) tem prioridade sobre inline
        desc_parts = desc_words or inline_desc
        desc = clean_text(" ".join(desc_parts)) or "Lançamento"
        txs.append(Transaction(date=dt, description=desc[:128], amount=amount, doc_type="checking"))

    return txs


# ─────────────────────────────────────────────
# Parser BRB — fatura  (double-encoded header, normal transactions)
# ─────────────────────────────────────────────

def parse_brb_fatura(pdf_path: str) -> list[Transaction]:
    """
    BRB fatura — header em double-encoding (DDAATTAA), transações em encoding normal.
    Sinal: + = gasto (negativo), - = pagamento (positivo).
    """
    txs = []
    year_hint = datetime.now().year

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
        p1_text = pdf.pages[0].extract_text() or ""
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", p1_text)
        if m:
            year_hint = int(m.group(3))

        for page in pdf.pages:
            lns = lines_by_y(page)
            for _, words in lns:
                row = " ".join(w["text"] for w in words).strip()
                # Ignorar linhas double-encoded (separadores de cartão)
                if re.search(r"([A-Z])\1{2,}", row):
                    continue
                if any(s in row for s in ["Transações nacionais", "Transações internacionais",
                                           "Total desse cartão", "ATENÇÃO"]):
                    continue
                m = TX_RE.match(row)
                if not m:
                    continue
                dt = parse_date(m.group(1), year_hint)
                if not dt:
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
                    date=dt,
                    description=clean_text(desc or raw_desc)[:128],
                    amount=amount,
                    memo=clean_text(memo),
                    doc_type="creditcard"
                ))

    return txs


# ─────────────────────────────────────────────
# Parser Sicoob — extrato
# ─────────────────────────────────────────────

def parse_sicoob_extrato(pdf_path: str) -> list[Transaction]:
    txs = []
    year_hint = datetime.now().year

    with pdfplumber.open(pdf_path) as pdf:
        all_text_lines = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_text_lines.extend(text.split("\n"))

    # Inferir ano do PERÍODO
    for line in all_text_lines:
        m = re.search(r"PERÍODO[:\s]+\d{2}/\d{2}/(\d{4})", line)
        if m:
            year_hint = int(m.group(1))
            break

    SICOOB_SKIP_EX = {"SALDO ANTERIOR", "SALDO BLOQ", "SALDO FINAL"}
    trans_re = re.compile(r"^(\d{2}/\d{2})\s+(.+?)\s+([\d\.]+,\d{2})([DC])$")
    i = 0
    while i < len(all_text_lines):
        line = all_text_lines[i].strip()
        m = trans_re.match(line)
        if m:
            dt = parse_date(m.group(1), year_hint)
            desc = m.group(2)
            amount = parse_br_value(m.group(3) + m.group(4))
            # Coletar memo nas linhas seguintes (DOC:, nome, CNPJ)
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


# ─────────────────────────────────────────────
# Parser Sicoob — fatura
# ─────────────────────────────────────────────

MESES = {"JAN":1,"FEV":2,"MAR":3,"ABR":4,"MAI":5,"JUN":6,
          "JUL":7,"AGO":8,"SET":9,"OUT":10,"NOV":11,"DEZ":12}

def parse_sicoob_fatura(pdf_path: str) -> list[Transaction]:
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
            # Em fatura, tudo é gasto (negativo)
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


# ─────────────────────────────────────────────
# Parser Bradesco — extrato (multi-linha, colunas Crédito/Débito)
# ─────────────────────────────────────────────

BRADESCO_SKIP = {"SALDO ANTERIOR", "SALDO INVEST", "SALDO APLIC"}

def parse_bradesco(pdf_path: str) -> list[Transaction]:
    """
    Bradesco Net Empresa — layout por grupo (3 linhas):
      [TIPO x=101]             ← nome da operação, sem data, sem valor
      [DATA x=41][DCTO][VALOR] ← linha principal
      [MEMO x=101]             ← remetente (opcional)

    Múltiplas transações no mesmo dia: linhas com valor mas sem data (herdam última data).
    Processamento por página para evitar confusão de coordenadas Y entre páginas.
    """
    txs = []
    saved_cols = None
    SKIP_TEXT = {"Folha", "Extrato Mensal", "Data da opera", "Os dados acima",
                 "Nome do usu", "Últimos Lançamentos", "SALDO INVEST", "Saldos Invest"}
    last_date = None  # herdada entre páginas

    def process_page_rows(rows):
        """Agrupa rows de uma página e emite transações."""
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


# ─────────────────────────────────────────────
# Detecção automática de banco
# ─────────────────────────────────────────────

def detect_and_parse(pdf_path: str) -> tuple[list[Transaction], str]:
    """
    Retorna (transactions, bank_name).
    bank_name é apenas informativo.
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(
            (page.extract_text() or "") for page in pdf.pages[:3]
        )
    up = text.upper()

    if "SICOOB" in up:
        if "PAGAMENTO MÍNIMO" in up or "VENCIMENTO" in up and "R$ 170.000" in text:
            return parse_sicoob_fatura(pdf_path), "sicoob_fatura"
        return parse_sicoob_extrato(pdf_path), "sicoob_extrato"

    if "33.264.668" in text or "BANCO XP" in up or "CONTA DIGITAL XP" in up:
        return parse_xp(pdf_path), "xp_extrato"

    if "60.701.190" in text or "ITAÚ" in text or "ITAU UNIBANCO" in up or "SISPAG" in up:
        return parse_itau(pdf_path), "itau_extrato"

    if "16.501.555" in text or "STONE.COM.BR" in up or "STONE INSTITUIÇÃO" in up:
        return parse_stone(pdf_path), "stone_extrato"

    if "60.746.948" in text or "BRADESCO" in up or "NET EMPRESA" in up or \
       ("BANCO TRIANGULO" in up) or \
       ("CRÉDITO (R$)" in text or "DÉBITO (R$)" in text or "Crédito (R$)" in text):
        return parse_bradesco(pdf_path), "bradesco_extrato"

    if "BRB" in up or "047.033.940" in text:
        if "LANÇAMENTOS" in up or "DDAATTAA" in text or "VENCIMENTO" in up and "FATURA" in up:
            return parse_brb_fatura(pdf_path), "brb_fatura"
        return parse_brb_extrato(pdf_path), "brb_extrato"

    raise ValueError(f"Banco não identificado em: {pdf_path}")


# ─────────────────────────────────────────────
# Saída JSON
# ─────────────────────────────────────────────

def to_json(transactions: list[Transaction], bank: str, source_file: str) -> dict:
    return {
        "source": Path(source_file).name,
        "bank": bank,
        "generated_at": datetime.now().isoformat(),
        "total_transactions": len(transactions),
        "transactions": [t.to_dict() for t in transactions],
    }


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python3 pdf_to_json.py arquivo.pdf [arquivo2.pdf ...]")
        sys.exit(1)

    for pdf_file in sys.argv[1:]:
        print(f"\nProcessando: {pdf_file}")
        try:
            txs, bank = detect_and_parse(pdf_file)
            out = to_json(txs, bank, pdf_file)
            out_path = Path(pdf_file).with_suffix(".json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            print(f"  Banco: {bank} | Transações: {len(txs)} | Saída: {out_path}")
        except Exception as e:
            print(f"  ERRO: {e}")
            raise
