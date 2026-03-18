from dataclasses import dataclass, asdict
from pydantic import BaseModel


@dataclass
class AccountMetadata:
    bankid: str = ""        # Codigo COMPE do banco (ex: "348" para XP)
    branchid: str = ""      # Agencia (ex: "0001")
    acctid: str = ""        # Numero da conta (ex: "11083694")
    acct_type: str = "CHECKING"  # "CHECKING" ou "CREDITCARD"
    balance: float = 0.0    # Saldo final do extrato
    balance_date: str = ""  # Data ISO do saldo

    def to_dict(self):
        return asdict(self)


class AccountMetadataSchema(BaseModel):
    bankid: str
    branchid: str
    acctid: str
    acct_type: str
    balance: float
    balance_date: str
