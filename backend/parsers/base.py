from abc import ABC, abstractmethod
from backend.models.transaction import Transaction
from backend.models.account_meta import AccountMetadata


class BaseBankParser(ABC):
    """Classe base para todos os parsers bancarios."""

    bank_name: str = ""
    doc_type: str = "checking"
    bank_code: str = ""  # Codigo COMPE do banco

    @abstractmethod
    def parse(self, pdf_path: str) -> list[Transaction]:
        """Parseia o PDF e retorna lista de Transaction."""
        ...

    @classmethod
    @abstractmethod
    def can_handle(cls, text: str) -> bool:
        """Dado o texto das primeiras paginas (raw), retorna True se este parser o reconhece."""
        ...

    def extract_metadata(self, pdf_path: str) -> AccountMetadata:
        """Extrai agencia, conta e saldo do PDF. Override nos parsers."""
        return AccountMetadata(
            bankid=self.bank_code,
            branchid="0001",
            acctid="0000000",
            acct_type="CHECKING" if self.doc_type == "checking" else "CREDITCARD",
            balance=0.0,
            balance_date=""
        )
