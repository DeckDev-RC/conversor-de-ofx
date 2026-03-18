from datetime import datetime
from pathlib import Path
import pdfplumber

from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata
from backend.parsers.base import BaseBankParser
from backend.parsers.sicoob_fatura import SicoobFaturaParser
from backend.parsers.sicoob_extrato import SicoobExtratoParser
from backend.parsers.xp import XPParser
from backend.parsers.itau import ItauParser
from backend.parsers.stone import StoneParser
from backend.parsers.bradesco import BradescoParser
from backend.parsers.brb_fatura import BRBFaturaParser
from backend.parsers.brb_extrato import BRBExtratoParser

# Ordem importa: fatura antes de extrato para BRB e Sicoob
PARSERS: list[type[BaseBankParser]] = [
    SicoobFaturaParser,
    SicoobExtratoParser,
    XPParser,
    ItauParser,
    StoneParser,
    BradescoParser,
    BRBFaturaParser,
    BRBExtratoParser,
]


def detect_and_parse(pdf_path: str) -> tuple[list[Transaction], str, AccountMetadata]:
    """Detecta o banco e parseia o PDF. Retorna (transactions, bank_name, metadata)."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(
            (page.extract_text() or "") for page in pdf.pages[:3]
        )

    for parser_cls in PARSERS:
        if parser_cls.can_handle(text):
            parser = parser_cls()
            txs = parser.parse(pdf_path)
            metadata = parser.extract_metadata(pdf_path)
            return txs, parser.bank_name, metadata

    raise ValueError(f"Banco não identificado em: {pdf_path}")


def to_json(transactions: list[Transaction], bank: str, source_file: str, metadata: AccountMetadata = None) -> dict:
    """Converte resultado do parse para dict JSON."""
    result = {
        "source": Path(source_file).name,
        "bank": bank,
        "generated_at": datetime.now().isoformat(),
        "total_transactions": len(transactions),
        "transactions": [t.to_dict() for t in transactions],
    }
    if metadata:
        result["metadata"] = metadata.to_dict()
    return result