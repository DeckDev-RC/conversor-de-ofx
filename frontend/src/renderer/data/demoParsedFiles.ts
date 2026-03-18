import type { ParsedFile, ParseResult, Transaction } from '../types'

function createTransaction(
  date: string,
  description: string,
  amount: number,
  fitid: string,
  docType: 'checking' | 'creditcard' = 'checking',
  memo = ''
): Transaction {
  return {
    date,
    description,
    amount,
    memo,
    doc_type: docType,
    raw_type: '',
    fitid,
  }
}

function createResult(
  source: string,
  bank: string,
  acctid: string,
  transactions: Transaction[],
  balance: number
): ParseResult {
  return {
    source,
    bank,
    generated_at: '2026-03-12T14:20:00.000000',
    total_transactions: transactions.length,
    transactions,
    metadata: {
      bankid: '000',
      branchid: '0001',
      acctid,
      acct_type: 'CHECKING',
      balance,
      balance_date: '2026-02-28',
    },
  }
}

function createFile(name: string, bank: string, acctid: string, balance: number, transactions: Transaction[]): ParsedFile {
  return {
    name,
    path: `demo/${name}`,
    status: 'done',
    result: createResult(name, bank, acctid, transactions, balance),
  }
}

export const demoParsedFiles: ParsedFile[] = [
  createFile('11-02 XP.pdf', 'xp_extrato', '11083694', 24.41, [
    createTransaction('2026-02-11', 'LIQUIDACAO CREDITO XP | 800562523', -5470.99, 'xp-01'),
    createTransaction('2026-02-09', 'LIQUIDACAO CREDITO XP | 500028827', -990.91, 'xp-02'),
    createTransaction('2026-02-05', 'Pix enviado para Azuos Assessoria Contabil Ltda', -500, 'xp-03'),
    createTransaction('2026-02-05', 'Pix recebido de Renan Leite Marques', 500, 'xp-04'),
    createTransaction('2026-02-04', 'Pix recebido de Wendell Coutinho de Bastos', 6788, 'xp-05'),
  ]),
  createFile('24-02 ITAU.pdf', 'itau_extrato', '99124501', 18843.1, [
    createTransaction('2026-02-24', 'Recebimento TED cliente recorrente', 14800, 'itau-01'),
    createTransaction('2026-02-24', 'Pagamento fornecedores lote 08', -6390.42, 'itau-02'),
    createTransaction('2026-02-22', 'Tarifa pacote empresarial', -89.9, 'itau-03'),
    createTransaction('2026-02-21', 'Pix recebido projeto mensal', 9400, 'itau-04'),
    createTransaction('2026-02-20', 'Aluguel escritorio', -2800, 'itau-05'),
  ]),
  createFile('24-02 STONE.pdf', 'stone_extrato', '45322018', 9620.77, [
    createTransaction('2026-02-24', 'Liquidacao vendas credito', 21540.32, 'stone-01'),
    createTransaction('2026-02-23', 'Chargeback ajuste bandeira', -830.41, 'stone-02'),
    createTransaction('2026-02-22', 'Liquidacao vendas debito', 4820.2, 'stone-03'),
    createTransaction('2026-02-21', 'Antecipacao recebiveis', 11990.55, 'stone-04'),
    createTransaction('2026-02-20', 'Taxas operacionais', -1245.88, 'stone-05'),
  ]),
  createFile('28-01BRB.pdf', 'brb_extrato', '88312007', 5200.5, [
    createTransaction('2026-01-28', 'Credito salario socios', 8800, 'brb-01'),
    createTransaction('2026-01-28', 'Pagamento folha operacional', -6124.92, 'brb-02'),
    createTransaction('2026-01-27', 'Pix recebido cliente avulso', 1780, 'brb-03'),
    createTransaction('2026-01-26', 'Transferencia enviada para reserva', -950, 'brb-04'),
  ]),
  createFile('BRB-FATURA.pdf', 'brb_fatura', '54881231', -1320.76, [
    createTransaction('2026-02-18', 'Hospedagem equipe comercial', -890.4, 'brbf-01', 'creditcard'),
    createTransaction('2026-02-14', 'Assinatura software financeiro', -249.9, 'brbf-02', 'creditcard'),
    createTransaction('2026-02-10', 'Passagem visita cliente', -1180.55, 'brbf-03', 'creditcard'),
    createTransaction('2026-02-08', 'Estorno parcial fornecedor', 310.12, 'brbf-04', 'creditcard'),
  ]),
  createFile('FATURASICOOB.pdf', 'sicoob_fatura', '12004477', -820.16, [
    createTransaction('2026-02-17', 'Combustivel equipe de campo', -420.32, 'sicf-01', 'creditcard'),
    createTransaction('2026-02-12', 'Material escritorio', -188.41, 'sicf-02', 'creditcard'),
    createTransaction('2026-02-09', 'Cafe com cliente', -92.17, 'sicf-03', 'creditcard'),
    createTransaction('2026-02-07', 'Estorno cartao corporativo', 41.5, 'sicf-04', 'creditcard'),
  ]),
]
