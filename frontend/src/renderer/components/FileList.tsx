import type { ParsedFile } from '../types'

interface FileListProps {
  files: ParsedFile[]
}

const statusConfig = {
  pending: {
    tone: 'text-text-muted',
    dot: 'bg-white/40',
    label: 'Pendente',
  },
  parsing: {
    tone: 'text-accent-yellow',
    dot: 'bg-accent-yellow',
    label: 'Processando',
  },
  done: {
    tone: 'text-accent-green',
    dot: 'bg-accent-green',
    label: 'Concluído',
  },
  error: {
    tone: 'text-accent-red',
    dot: 'bg-accent-red',
    label: 'Erro',
  },
} as const

export default function FileList({ files }: FileListProps) {
  if (files.length === 0) return null

  const completed = files.filter(file => file.status === 'done').length
  const errors = files.filter(file => file.status === 'error').length
  const pending = files.length - completed - errors
  const doneWidth = (completed / files.length) * 100
  const pendingWidth = (pending / files.length) * 100
  const errorWidth = (errors / files.length) * 100

  return (
    <aside className="panel flex flex-col p-5 lg:p-6">
      <div className="flex items-center justify-between gap-3">
        <span className="badge-muted">{files.length} arquivos</span>
      </div>

      <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-white/[0.06]">
        {doneWidth > 0 && <div className="h-full bg-accent-green" style={{ width: `${doneWidth}%` }} />}
        {pendingWidth > 0 && <div className="h-full bg-brand-amber" style={{ width: `${pendingWidth}%` }} />}
        {errorWidth > 0 && <div className="h-full bg-accent-red" style={{ width: `${errorWidth}%` }} />}
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2">
        <div className="metric-chip">
          <p className="metric-chip-label">Concluídos</p>
          <p className="metric-chip-value text-accent-green">{completed}</p>
        </div>
        <div className="metric-chip">
          <p className="metric-chip-label">Pendentes</p>
          <p className="metric-chip-value">{pending}</p>
        </div>
        <div className="metric-chip">
          <p className="metric-chip-label">Falhas</p>
          <p className="metric-chip-value text-accent-red">{errors}</p>
        </div>
      </div>

      <div className="mt-5 max-h-[28rem] space-y-2.5 overflow-auto pr-1">
        {files.map((file, index) => {
          const config = statusConfig[file.status]

          return (
            <div
              key={`${file.path}-${index}`}
              className="rounded-nf-lg border border-white/[0.08] bg-white/[0.025] p-3.5 transition-all duration-200 hover:bg-white/[0.04]"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-text-primary">{file.name}</p>
                  {file.result && (
                    <p className="mt-1 truncate text-xs text-text-secondary">
                      {file.result.bank} - {file.result.total_transactions} transações
                      {file.result.metadata && file.result.metadata.acctid !== '0000000' && ` - ${file.result.metadata.acctid}`}
                    </p>
                  )}
                  {file.error && <p className="mt-1 text-xs text-accent-red">{file.error}</p>}
                </div>

                <span className={`shrink-0 text-[10px] font-semibold uppercase tracking-[0.16em] ${config.tone}`}>
                  {config.label}
                </span>
              </div>
          </div>
          )
        })}
      </div>
    </aside>
  )
}
