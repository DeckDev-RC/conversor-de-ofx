from typing import Optional
from pydantic import BaseModel
from .transaction import TransactionSchema
from .account_meta import AccountMetadataSchema


class ParseResultSchema(BaseModel):
    source: str
    bank: str
    generated_at: str
    total_transactions: int
    transactions: list[TransactionSchema]
    metadata: Optional[AccountMetadataSchema] = None
