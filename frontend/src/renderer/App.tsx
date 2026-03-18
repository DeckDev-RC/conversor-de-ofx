import { useEffect, useMemo, useRef, useState } from 'react'
import Navbar from './components/Navbar'
import DropZone from './components/DropZone'
import FileList from './components/FileList'
import SummaryCard from './components/SummaryCard'
import FilterBar from './components/FilterBar'
import TransactionTable from './components/TransactionTable'
import InsightsPanel from './components/InsightsPanel'
import { useParseFiles } from './hooks/useParseFiles'
import { useTransactions } from './hooks/useTransactions'
import { demoParsedFiles } from './data/demoParsedFiles'

type BackendStatus = 'connecting' | 'starting' | 'ready' | 'error'
type TabId = 'import' | 'dashboard'

function formatCurrency(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatShortNumber(value: number): string {
  return new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function formatDateRange(dates: string[]): string {
  if (dates.length === 0) return 'Nenhum período visível'

  const sorted = [...dates].sort()
  const formatter = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })
  const start = formatter.format(new Date(`${sorted[0]}T00:00:00`))
  const end = formatter.format(new Date(`${sorted[sorted.length - 1]}T00:00:00`))

  return start === end ? start : `${start} - ${end}`
}

export default function App() {
  const searchParams = new URLSearchParams(window.location.search)
  const isDesktop = Boolean(window.electronAPI)
  const previewMode = !isDesktop && searchParams.get('demo') === '1'

  const [backendStatus, setBackendStatus] = useState<BackendStatus>(previewMode ? 'ready' : 'connecting')
  const [activeTab, setActiveTab] = useState<TabId>(
    previewMode && searchParams.get('tab') === 'dashboard' ? 'dashboard' : 'import'
  )

  const { files, addFiles, clearFiles, allTransactions, isLoading } = useParseFiles(previewMode ? demoParsedFiles : [])
  const { filtered, filters, setFilters, banks, summary, sortField, sortDir, toggleSort } = useTransactions(allTransactions)

  useEffect(() => {
    if (!window.electronAPI) return
    window.electronAPI.onBackendStatus((status: string) => {
      setBackendStatus(status as BackendStatus)
    })
  }, [])

  const successfulFiles = useMemo(() => files.filter(file => file.status === 'done' && file.result), [files])
  const hasResults = successfulFiles.length > 0
  const failedFiles = files.filter(file => file.status === 'error').length
  const processingFiles = files.filter(file => file.status === 'parsing').length

  const uniqueBanks = useMemo(() => {
    return new Set(successfulFiles.map(file => file.result?.bank).filter(Boolean)).size
  }, [successfulFiles])

  const visibleRange = useMemo(() => {
    return formatDateRange(filtered.map(transaction => transaction.date))
  }, [filtered])

  const visibleBanks = useMemo(() => {
    return new Set(filtered.map(transaction => transaction._bank)).size
  }, [filtered])

  const didAutoSwitch = useRef(false)
  useEffect(() => {
    if (hasResults && !didAutoSwitch.current) {
      didAutoSwitch.current = true
      setActiveTab('dashboard')
    }
    if (!hasResults) {
      didAutoSwitch.current = false
    }
  }, [hasResults])

  const handleClear = () => {
    clearFiles()
    setActiveTab('import')
  }

  const importHighlights = hasResults
    ? [
        {
          label: 'Arquivos',
          value: successfulFiles.length.toString(),
          note: failedFiles ? `${failedFiles} com erro` : '',
        },
        {
          label: 'Bancos',
          value: uniqueBanks.toString(),
          note: processingFiles ? `${processingFiles} processando` : '',
        },
        {
          label: 'Movimentos',
          value: formatShortNumber(allTransactions.length),
          note: visibleRange,
        },
      ]
    : [
        { label: 'Bancos', value: '6+', note: '' },
        { label: 'Saída', value: 'JSON / OFX', note: '' },
        { label: 'Revisão', value: 'Tabela', note: '' },
      ]

  return (
    <div className="page-shell min-h-screen flex flex-col bg-surface-200">
      <div className="pointer-events-none absolute inset-x-0 top-0 z-0 h-[26rem] bg-[radial-gradient(circle_at_top_center,rgba(130,160,255,0.14),transparent_28%)]" />
      <div className="pointer-events-none absolute left-[-4rem] top-[28rem] z-0 h-[20rem] w-[20rem] rounded-full bg-[radial-gradient(circle,rgba(169,161,255,0.08),transparent_70%)] blur-3xl" />
      <div className="pointer-events-none absolute right-[-4rem] top-[36rem] z-0 h-[20rem] w-[20rem] rounded-full bg-[radial-gradient(circle,rgba(130,160,255,0.08),transparent_70%)] blur-3xl" />

      <Navbar
        isDesktop={isDesktop}
        backendStatus={backendStatus}
        hasResults={hasResults}
        files={files}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onClear={handleClear}
      />

      <main className="relative z-10 flex-1 overflow-auto">
        <div className="mx-auto flex w-full max-w-[1500px] flex-col gap-8 px-5 pb-10 pt-8 lg:px-8">
          {activeTab === 'import' && (
            <div className="space-y-6 animate-fade-in">
              {!hasResults ? (
                <div className="flex flex-col items-center justify-center py-8 lg:py-16">
                  <div className="w-full max-w-[680px]">
                    <DropZone isDesktop={isDesktop} onFiles={addFiles} isLoading={isLoading} />
                  </div>
                </div>
              ) : (
                <section className="workspace-shell">
                  <div className="workspace-toolbar">
                    <span className="badge-muted">{successfulFiles.length} arquivos prontos</span>
                    <span className="badge-muted">{uniqueBanks} bancos</span>
                    <span className="badge-muted">{formatShortNumber(allTransactions.length)} movimentos</span>
                  </div>
                  <div className="grid gap-5 p-5 lg:p-6 xl:grid-cols-[minmax(0,1fr)_340px]">
                    <DropZone isDesktop={isDesktop} onFiles={addFiles} isLoading={isLoading} />
                    <FileList files={files} />
                  </div>
                </section>
              )}
            </div>
          )}

          {activeTab === 'dashboard' && hasResults && (
            <div className="space-y-6 animate-fade-in">
              <section className="workspace-shell">
                <div className="workspace-toolbar">
                  <div className="badge-muted">{visibleRange}</div>
                  <div className="badge-muted">{successfulFiles.length} arquivos</div>
                  <div className="badge-muted">{visibleBanks} bancos</div>
                  <div className="badge-muted">{filtered.length} transações</div>
                  {previewMode && <div className="badge-muted text-brand-amber">Preview</div>}
                </div>

                <div className="p-5 lg:p-6">
                  <div className="panel-soft p-6">
                    <p className="label-muted">Saldo líquido</p>
                    <p
                      className={`mt-3 font-display text-5xl leading-none ${
                        summary.net >= 0 ? 'text-accent-green' : 'text-accent-red'
                      }`}
                    >
                      {formatCurrency(summary.net)}
                    </p>

                    <div className="mt-5 grid gap-3 sm:grid-cols-3">
                      <div className="metric-chip">
                        <p className="metric-chip-label">Bancos</p>
                        <p className="metric-chip-value">{visibleBanks.toLocaleString('pt-BR')}</p>
                      </div>
                      <div className="metric-chip">
                        <p className="metric-chip-label">Arquivos</p>
                        <p className="metric-chip-value">{successfulFiles.length.toLocaleString('pt-BR')}</p>
                      </div>
                      <div className="metric-chip">
                        <p className="metric-chip-label">Ticket médio</p>
                        <p className="metric-chip-value">{formatCurrency(summary.averageTicket)}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              <SummaryCard summary={summary} />
              <InsightsPanel transactions={filtered} summary={summary} />
              <FilterBar filters={filters} setFilters={setFilters} banks={banks} />
              <TransactionTable
                transactions={filtered}
                sortField={sortField}
                sortDir={sortDir}
                toggleSort={toggleSort}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
