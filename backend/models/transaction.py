import uuid
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel


@dataclass
class Transaction:
    date: str          # ISO 8601 "YYYY-MM-DD"
    description: str   # texto limpo, sem duplo espaco
    amount: float      # negativo = debito, positivo = credito
    memo: str = ""     # info complementar (CNPJ, contraparte, doc)
    doc_type: str = "checking"   # "checking" | "creditcard"
    raw_type: str = ""  # tipo original do banco (ex: "Entrada", "D", "C")
    fitid: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self):
        return asdict(self)


class TransactionSchema(BaseModel):
    date: str
    description: str
    amount: float
    memo: str
    doc_type: str
    raw_type: str
    fitid: str
