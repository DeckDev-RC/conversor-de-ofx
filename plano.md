Context
O backend ja parseia PDFs de 6 bancos brasileiros em JSON (Fase 1 concluida). O proximo passo e converter esses JSONs em arquivos OFX v102 validos para importacao no Conta Azul. Isso envolve:

Extrair metadados bancarios (agencia, conta, saldo) dos PDFs — atualmente nao extraidos
Criar modulo gerador de OFX no backend
Novo endpoint /export-ofx na API
Botao "Exportar OFX" no frontend

Decisoes ja tomadas pelo usuario:

Metadados: extrair automaticamente dos PDFs (nao pedir ao usuario)
Datas: usar 120000 como hora padrao (YYYYMMDD120000[-3:GMT])
Cartao de credito: usar CCSTMTRS (estrutura propria), extratos usam STMTRS


Novos Arquivos
backend/
├── models/
│   └── account_meta.py        # NOVO - AccountMetadata dataclass
├── parsers/
│   └── (8 parsers existentes)  # MODIFICAR - adicionar extract_metadata()
├── ofx/
│   ├── __init__.py
│   ├── generator.py           # NOVO - gera string OFX a partir de ParseResult+Metadata
│   ├── sanitizer.py           # NOVO - sanitiza texto para OFX (& → e, < → (, etc.)
│   └── constants.py           # NOVO - BANK_CODES, OFX_HEADER template
├── main.py                    # MODIFICAR - adicionar POST /export-ofx
└── cli.py                     # MODIFICAR - adicionar flag --ofx

Passo 1: AccountMetadata — backend/models/account_meta.py
Novo dataclass para metadados bancarios extraidos do PDF:
python@dataclass
class AccountMetadata:
    bankid: str        # Codigo COMPE do banco (ex: "348" para XP)
    branchid: str      # Agencia (ex: "0001")
    acctid: str        # Numero da conta (ex: "11083694")
    acct_type: str     # "CHECKING" ou "CREDITCARD"
    balance: float     # Saldo final do extrato (0.0 se nao encontrado)
    balance_date: str  # Data ISO do saldo (ultima transacao se nao encontrado)
Tabela de codigos COMPE (fixos por parser):
ParserBANKIDObservacaoXP348Banco XP S.A.Itau341Itau UnibancoStone197Stone PagamentosBRB070BRB - Banco de BrasiliaSicoob756Bancoob/SicoobBradesco237Bradesco
Atualizar backend/models/__init__.py para exportar AccountMetadata.
Atualizar backend/models/parse_result.py — adicionar campo metadata: AccountMetadataSchema opcional.

Passo 2: Modificar BaseBankParser — backend/parsers/base.py
Adicionar metodo extract_metadata() a classe base:
pythonclass BaseBankParser(ABC):
    bank_name: str = ""
    doc_type: str = "checking"
    bank_code: str = ""  # NOVO - codigo COMPE

    @abstractmethod
    def parse(self, pdf_path: str) -> list[Transaction]: ...

    @classmethod
    @abstractmethod
    def can_handle(cls, text: str) -> bool: ...

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

Passo 3: Adicionar extract_metadata() em cada parser
Cada parser tera logica especifica para encontrar agencia, conta e saldo no PDF:
XP (backend/parsers/xp.py)

bank_code = "348"
Agencia/Conta: buscar regex Ag\w*[:\s]+(\d+) e Conta[:\s]+(\d+) nas primeiras paginas
Saldo: capturar valor na coluna x_saldo da ultima transacao

Itau (backend/parsers/itau.py)

bank_code = "341"
Agencia/Conta: buscar regex AG[ÊE]NCIA[:\s]+(\d+) e CONTA[:\s]+([\d\-]+) no header
Saldo: a coluna "Saldo" ja tem posicao (saved_cols["saldo"]) — capturar ultimo valor

Stone (backend/parsers/stone.py)

bank_code = "197"
Agencia/Conta: linhas "Agência" e "Conta" estao no SKIP_ROWS — remover do skip e capturar valores
Saldo: coluna SALDO ja mapeada (saved_cols["saldo"])

BRB Extrato (backend/parsers/brb_extrato.py)

bank_code = "070"
Agencia/Conta: linhas "Agência" e "Conta Corrente" estao no SKIP — capturar antes de pular
Saldo: ultimo valor VAL_RE encontrado no parse

BRB Fatura (backend/parsers/brb_fatura.py)

bank_code = "070"
Conta: buscar numero do cartao na primeira pagina
Saldo: total da fatura (soma dos valores ou linha "Total")

Sicoob Extrato (backend/parsers/sicoob_extrato.py)

bank_code = "756"
Agencia/Conta: buscar no header acima da tabela de transacoes
Saldo: linha "SALDO FINAL" que e filtrada no skip — capturar valor antes de pular

Sicoob Fatura (backend/parsers/sicoob_fatura.py)

bank_code = "756"
Conta: buscar numero do cartao
Saldo: linha "TOTAL R$" — capturar valor

Bradesco (backend/parsers/bradesco.py)

bank_code = "237"
Agencia/Conta: buscar no header antes da tabela
Saldo: coluna "Saldo" ja mapeada — capturar ultimo valor

Estrategia: Cada parser ganha bank_code como atributo de classe e implementa extract_metadata(). Se nao encontrar algum dado, retorna o default do base.

Passo 4: Modificar detect_and_parse() — backend/parsers/__init__.py
pythondef detect_and_parse(pdf_path: str) -> tuple[list[Transaction], str, AccountMetadata]:
    # ... detecta parser ...
    parser = parser_cls()
    txs = parser.parse(pdf_path)
    metadata = parser.extract_metadata(pdf_path)
    return txs, parser.bank_name, metadata
Atualizar to_json() para incluir metadata no resultado:
pythondef to_json(transactions, bank, source_file, metadata=None):
    result = { ...campos existentes... }
    if metadata:
        result["metadata"] = {
            "bankid": metadata.bankid,
            "branchid": metadata.branchid,
            "acctid": metadata.acctid,
            "acct_type": metadata.acct_type,
            "balance": metadata.balance,
            "balance_date": metadata.balance_date,
        }
    return result

Passo 5: Modulo OFX — backend/ofx/
5.1 backend/ofx/constants.py
pythonOFX_HEADER = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
"""

TIMEZONE = "[-3:GMT]"
DEFAULT_TIME = "120000"
5.2 backend/ofx/sanitizer.py
pythondef sanitize_ofx_text(text: str) -> str:
    """Sanitiza texto para OFX: & → e, < → (, > → ), max 255 chars."""
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('&', 'e')
    text = text.replace('<', '(')
    text = text.replace('>', ')')
    return text[:255]

def format_ofx_date(iso_date: str) -> str:
    """'2026-02-04' → '20260204120000[-3:GMT]'"""
    return iso_date.replace('-', '') + DEFAULT_TIME + TIMEZONE

def format_ofx_amount(amount: float) -> str:
    """Formata valor para OFX: ponto decimal, 2 casas, com sinal."""
    return f"{amount:.2f}"
5.3 backend/ofx/generator.py
Funcao principal generate_ofx():
pythondef generate_ofx(parse_result: dict) -> str:
    """Gera string OFX completa a partir de um ParseResult com metadata."""
Logica:

Ordenar transacoes por data crescente, depois por fitid
Gerar FITID como hash de dtposted|amount|description
Determinar DTSTART (primeira tx) e DTEND (ultima tx)
Para cada transacao:

TRNTYPE: CREDIT se amount > 0, DEBIT se amount < 0
DTPOSTED: format_ofx_date(tx.date)
TRNAMT: format_ofx_amount(tx.amount)
FITID: hash unico
NAME: sanitize_ofx_text(tx.description)
SEM tag MEMO (removido propositalmente)


LEDGERBAL com saldo real do metadata
Tags todas fechadas corretamente

Dois templates:

_generate_checking_ofx() — usa BANKMSGSRSV1 > STMTRS > BANKACCTFROM
_generate_creditcard_ofx() — usa CREDITCARDMSGSRSV1 > CCSTMTRS > CCACCTFROM

Selecao por metadata.acct_type.

Passo 6: Novo endpoint — backend/main.py
python@app.post("/export-ofx")
async def export_ofx(files: list[UploadFile] = File(...)):
    """Parseia PDFs e retorna lista de {filename, ofx_content}."""
    results = []
    for file in files:
        txs, bank, metadata = detect_and_parse(tmp_path)
        ofx_str = generate_ofx(to_json(txs, bank, file.filename, metadata))
        results.append({"filename": file.filename.replace('.pdf', '.ofx'), "content": ofx_str})
    return results

Passo 7: Frontend — Adicionar exportacao OFX
7.1 Atualizar tipos — frontend/src/renderer/types/index.ts

Adicionar AccountMetadata interface
Adicionar metadata? campo em ParseResult
Adicionar exportOFX em ElectronAPI

7.2 Atualizar preload — frontend/src/preload/index.ts

Expor novo IPC: exportOFX: (filePaths) => ipcRenderer.invoke('export-ofx', filePaths)

7.3 Atualizar main process — frontend/src/main/index.ts

Novo handler export-ofx:

Chama endpoint /export-ofx do backend
Abre dialog para escolher pasta destino
Salva cada arquivo .ofx



7.4 Atualizar python-bridge — frontend/src/main/python-bridge.ts

Nova funcao exportOFX(filePaths) que chama POST /export-ofx

7.5 Atualizar ExportButton — frontend/src/renderer/components/ExportButton.tsx

Dois botoes: "Exportar JSON" e "Exportar OFX"
Ou dropdown com opcoes de formato

7.6 Atualizar useParseFiles — frontend/src/renderer/hooks/useParseFiles.ts

Guardar os paths originais dos PDFs para reenviar ao endpoint /export-ofx

7.7 Atualizar ParseResult display

Mostrar metadata (banco, agencia, conta) no FileList ou SummaryCard


Passo 8: Atualizar CLI — backend/cli.py
Adicionar flag --ofx:
bashpython -m backend.cli arquivo.pdf              # gera JSON (padrao)
python -m backend.cli --ofx arquivo.pdf        # gera OFX
python -m backend.cli --ofx --json arquivo.pdf # gera ambos

Ordem de Implementacao

AccountMetadata model + atualizar ParseResult
bank_code em cada parser + extract_metadata() no base
extract_metadata() em cada parser (8 arquivos)
Atualizar detect_and_parse() e to_json() para incluir metadata
Modulo OFX (constants, sanitizer, generator)
Endpoint /export-ofx no main.py
Testar backend — gerar OFX de cada PDF e validar estrutura
Frontend — tipos, IPC, botao, bridge
CLI com flag --ofx


Verificacao

Para cada PDF sample, gerar OFX e verificar:

Header OFX v102 correto
BANKID/BRANCHID/ACCTID preenchidos (nao placeholder)
Transacoes em ordem cronologica crescente
TRNTYPE coerente com sinal do TRNAMT
FITID unico por transacao
NAME sanitizado (sem &, <, >)
LEDGERBAL com saldo real
Tags todas fechadas
Faturas usam CCSTMTRS, extratos usam STMTRS


Testar importacao no Conta Azul (manual pelo usuario)
Testar via frontend: arrastar PDF → ver tabela → exportar OFX


Arquivos a Modificar
ArquivoAcaobackend/models/account_meta.pyCRIARbackend/models/__init__.pyMODIFICAR — exportar AccountMetadatabackend/models/parse_result.pyMODIFICAR — adicionar metadatabackend/parsers/base.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/xp.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/itau.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/stone.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/brb_extrato.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/brb_fatura.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/sicoob_extrato.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/sicoob_fatura.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/bradesco.pyMODIFICAR — bank_code + extract_metadata()backend/parsers/__init__.pyMODIFICAR — detect_and_parse retorna metadatabackend/ofx/__init__.pyCRIARbackend/ofx/constants.pyCRIARbackend/ofx/sanitizer.pyCRIARbackend/ofx/generator.pyCRIARbackend/main.pyMODIFICAR — endpoint /export-ofxbackend/cli.pyMODIFICAR — flag --ofxfrontend/src/renderer/types/index.tsMODIFICARfrontend/src/preload/index.tsMODIFICARfrontend/src/main/index.tsMODIFICARfrontend/src/main/python-bridge.tsMODIFICARfrontend/src/renderer/components/ExportButton.tsxMODIFICARfrontend/src/renderer/hooks/useParseFiles.tsMODIFICAR