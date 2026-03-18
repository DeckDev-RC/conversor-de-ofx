import type { SortDirection, SortField } from '../types'

interface TransactionRow {
  date: string
  description: string
  amount: number
  memo: string
  doc_type: 'checking' | 'creditcard'
  raw_type: string
  fitid: string
  _bank: string
  _source: string
}

interface TransactionTableProps {
  transactions: TransactionRow[]
  sortField: SortField
  sortDir: SortDirection
  toggleSort: (field: SortField) => void
}

const BANK_LABELS: Record<string, string> = {
  xp_extrato: 'XP',
  itau_extrato: 'Itau',
  stone_extrato: 'Stone',
  brb_extrato: 'BRB',
  brb_fatura: 'BRB Fatura',
  sicoob_extrato: 'Sicoob',
  sicoob_fatura: 'Sicoob Fatura',
  bradesco_extrato: 'Bradesco',
}

function formatBRL(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}/${month}/${year}`
}

function SortIcon({ field, currentField, dir }: { field: SortField; currentField: SortField; dir: SortDirection }) {
  if (field !== currentField) {
    return (
      <svg className="ml-1 inline-block h-3 w-3 text-text-disabled" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
      </svg>
    )
  }

  return (
    <svg
      className="ml-1 inline-block h-3 w-3 text-brand-amber transition-transform duration-200"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      strokeWidth={2.5}
      style={{ transform: dir === 'asc' ? 'rotate(0deg)' : 'rotate(180deg)' }}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
    </svg>
  )
}

export default function TransactionTable({ transactions, sortField, sortDir, toggleSort }: TransactionTableProps) {
  if (transactions.length === 0) {
    return (
      <div className="panel flex flex-col items-center justify-center px-6 py-12 text-center">
        <h3 className="font-display text-[1.6rem] text-text-primary">Nenhuma transação encontrada</h3>
        <p className="mt-2 text-sm text-text-secondary">Ajuste os filtros para ampliar o recorte.</p>
      </div>
    )
  }

  const columns: { key: SortField; label: string; className?: string }[] = [
    { key: 'date', label: 'Data', className: 'w-28' },
    { key: 'bank', label: 'Banco', className: 'w-36' },
    { key: 'description', label: 'Descrição' },
    { key: 'amount', label: 'Valor', className: 'w-44 text-right' },
    { key: 'doc_type', label: 'Tipo', className: 'w-28' },
  ]

  return (
    <section className="panel overflow-hidden">
      <div className="flex items-end justify-between gap-4 border-b border-white/10 px-5 py-4">
        <div>
          <p className="section-kicker">Ledger</p>
          <h3 className="mt-2 font-display text-[1.9rem] text-text-primary">Transações</h3>
        </div>
      </div>

      <div className="max-h-[62vh] overflow-auto">
        <table className="w-full min-w-[920px] text-sm">
          <thead className="sticky top-0 z-10 bg-[rgba(7,14,13,0.96)] backdrop-blur-xl">
            <tr>
              {columns.map(column => (
                <th
                  key={column.key}
                  className={`px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted ${column.className || ''}`}
                >
                  <button
                    type="button"
                    className="inline-flex items-center hover:text-text-primary"
                    onClick={() => toggleSort(column.key)}
                  >
                    {column.label}
                    <SortIcon field={column.key} currentField={sortField} dir={sortDir} />
                  </button>
                </th>
              ))}
              <th className="px-5 py-4 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">Memo</th>
            </tr>
          </thead>

          <tbody>
            {transactions.map((transaction, index) => (
              <tr key={`${transaction.fitid}-${index}`} className="border-t border-white/[0.06] transition-colors duration-150 hover:bg-white/[0.035]">
                <td className="px-5 py-4 font-mono text-[12px] tracking-[0.08em] text-text-secondary">
                  {formatDate(transaction.date)}
                </td>
                <td className="px-5 py-4">
                  <span className="badge-muted">{BANK_LABELS[transaction._bank] || transaction._bank}</span>
                </td>
                <td className="px-5 py-4">
                  <p className="max-w-[28rem] truncate text-sm font-medium text-text-primary" title={transaction.description}>
                    {transaction.description}
                  </p>
                  <p className="mt-1 text-xs text-text-muted">{transaction._source}</p>
                </td>
                <td className={`px-5 py-4 text-right font-mono text-[13px] font-semibold ${transaction.amount >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {formatBRL(transaction.amount)}
                </td>
                <td className="px-5 py-4">
                  <span className={transaction.doc_type === 'checking' ? 'badge-blue' : 'badge-purple'}>
                    {transaction.doc_type === 'checking' ? 'Extrato' : 'Fatura'}
                  </span>
                </td>
                <td className="px-5 py-4 text-xs text-text-muted" title={transaction.memo}>
                  <p className="max-w-[18rem] truncate">{transaction.memo || 'Sem memo'}</p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
