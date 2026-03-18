import { useMemo } from 'react'
import type { SummaryMetrics, TransactionRecord } from '../types'

interface InsightsPanelProps {
  transactions: TransactionRecord[]
  summary: SummaryMetrics
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
  return `${day}/${month}/${year.slice(2)}`
}

function buildLinePath(points: { x: number; y: number }[]): string {
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
}

function buildAreaPath(points: { x: number; y: number }[], baseline: number): string {
  if (points.length === 0) return ''

  const linePath = buildLinePath(points)
  const lastPoint = points[points.length - 1]
  const firstPoint = points[0]
  return `${linePath} L ${lastPoint.x} ${baseline} L ${firstPoint.x} ${baseline} Z`
}

function SegmentedBar({
  segments,
}: {
  segments: { label: string; value: number; color: string; textColor: string }[]
}) {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0)

  return (
    <div className="space-y-2.5">
      <div className="flex h-3 overflow-hidden rounded-full bg-white/[0.06]">
        {segments.map(segment => (
          <div
            key={segment.label}
            className={segment.color}
            style={{ width: `${total > 0 ? (segment.value / total) * 100 : 0}%` }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {segments.map(segment => (
          <span key={segment.label} className={`badge-muted ${segment.textColor}`}>
            {segment.label}: {total > 0 ? Math.round((segment.value / total) * 100) : 0}%
          </span>
        ))}
      </div>
    </div>
  )
}

export default function InsightsPanel({ transactions, summary }: InsightsPanelProps) {
  const dailySeries = useMemo(() => {
    const grouped = new Map<
      string,
      { date: string; net: number; credits: number; debits: number; volume: number; count: number }
    >()

    for (const transaction of transactions) {
      const current = grouped.get(transaction.date) ?? {
        date: transaction.date,
        net: 0,
        credits: 0,
        debits: 0,
        volume: 0,
        count: 0,
      }

      current.net += transaction.amount
      current.volume += Math.abs(transaction.amount)
      current.count += 1

      if (transaction.amount >= 0) {
        current.credits += transaction.amount
      } else {
        current.debits += Math.abs(transaction.amount)
      }

      grouped.set(transaction.date, current)
    }

    return Array.from(grouped.values()).sort((left, right) => left.date.localeCompare(right.date))
  }, [transactions])

  const bankSeries = useMemo(() => {
    const grouped = new Map<string, { bank: string; volume: number; net: number; count: number }>()

    for (const transaction of transactions) {
      const current = grouped.get(transaction._bank) ?? {
        bank: transaction._bank,
        volume: 0,
        net: 0,
        count: 0,
      }

      current.volume += Math.abs(transaction.amount)
      current.net += transaction.amount
      current.count += 1
      grouped.set(transaction._bank, current)
    }

    return Array.from(grouped.values()).sort((left, right) => right.volume - left.volume)
  }, [transactions])

  const docTypeSegments = useMemo(() => {
    const checking = transactions.filter(transaction => transaction.doc_type === 'checking').length
    const creditcard = transactions.length - checking

    return [
      { label: 'Extrato', value: checking, color: 'bg-accent-blue', textColor: 'text-accent-blue' },
      { label: 'Fatura', value: creditcard, color: 'bg-accent-purple', textColor: 'text-accent-purple' },
    ]
  }, [transactions])

  const movementSegments = useMemo(() => {
    return [
      { label: 'Créditos', value: summary.credits, color: 'bg-accent-green', textColor: 'text-accent-green' },
      { label: 'Débitos', value: Math.abs(summary.debits), color: 'bg-accent-red', textColor: 'text-accent-red' },
    ]
  }, [summary.credits, summary.debits])

  const chart = useMemo(() => {
    if (dailySeries.length === 0) return null

    const width = 760
    const height = 240
    const paddingX = 18
    const paddingY = 22
    const baseline = height / 2
    const maxAbsNet = Math.max(...dailySeries.map(item => Math.abs(item.net)), 1)
    const scale = (height / 2 - paddingY) / maxAbsNet
    const step = dailySeries.length === 1 ? 0 : (width - paddingX * 2) / (dailySeries.length - 1)

    const points = dailySeries.map((item, index) => ({
      x: paddingX + step * index,
      y: baseline - item.net * scale,
    }))

    return {
      width,
      height,
      baseline,
      points,
      linePath: buildLinePath(points),
      areaPath: buildAreaPath(points, baseline),
      gridLines: [0.1, 0.3, 0.5, 0.7, 0.9].map(stop => height * stop),
    }
  }, [dailySeries])

  const biggestCreditDay = dailySeries.reduce(
    (best, item) => (item.credits > best.credits ? item : best),
    dailySeries[0] ?? { date: '', credits: 0, debits: 0, net: 0, volume: 0, count: 0 }
  )

  const biggestDebitDay = dailySeries.reduce(
    (best, item) => (item.debits > best.debits ? item : best),
    dailySeries[0] ?? { date: '', credits: 0, debits: 0, net: 0, volume: 0, count: 0 }
  )

  const averagePerDay = dailySeries.length > 0 ? summary.volume / dailySeries.length : 0
  const maxBankVolume = bankSeries[0]?.volume ?? 1

  if (transactions.length === 0) {
    return null
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.75fr)]">
      <article className="panel p-5 lg:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-xl">
            <p className="section-kicker">Insights</p>
            <h3 className="mt-2 font-display text-[1.95rem] text-text-primary">Fluxo diário</h3>
          </div>

          <div className="rounded-nf-lg border border-white/[0.08] bg-white/[0.03] px-4 py-3">
            <p className="label-muted">Média por dia</p>
            <p className="mt-2 font-display text-[1.9rem] text-text-primary">{formatBRL(averagePerDay)}</p>
          </div>
        </div>

        {chart && (
          <div className="mt-6 overflow-hidden rounded-nf-xl border border-white/[0.08] bg-[linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01))] p-4">
            <svg viewBox={`0 0 ${chart.width} ${chart.height}`} className="h-[17rem] w-full">
              <defs>
                <linearGradient id="flow-area" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(130,160,255,0.32)" />
                  <stop offset="100%" stopColor="rgba(130,160,255,0.02)" />
                </linearGradient>
                <linearGradient id="flow-line" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#82A0FF" />
                  <stop offset="100%" stopColor="#A9A1FF" />
                </linearGradient>
              </defs>

              <rect x="0" y="0" width={chart.width} height={chart.height} fill="transparent" />

              {chart.gridLines.map(line => (
                <line
                  key={line}
                  x1="0"
                  y1={line}
                  x2={chart.width}
                  y2={line}
                  stroke="rgba(255,255,255,0.06)"
                  strokeDasharray="6 10"
                />
              ))}

              <line
                x1="0"
                y1={chart.baseline}
                x2={chart.width}
                y2={chart.baseline}
                stroke="rgba(255,255,255,0.18)"
                strokeDasharray="8 10"
              />

              <path d={chart.areaPath} fill="url(#flow-area)" />
              <path
                d={chart.linePath}
                fill="none"
                stroke="url(#flow-line)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {chart.points.map((point, index) => (
                <g key={`${dailySeries[index].date}-${index}`}>
                  <circle cx={point.x} cy={point.y} r="5" fill="#0B0D12" stroke="#A6B1FF" strokeWidth="2" />
                  <text
                    x={point.x}
                    y={chart.height - 10}
                    textAnchor="middle"
                    fill="rgba(245,241,232,0.46)"
                    fontSize="11"
                    letterSpacing="0.08em"
                  >
                    {formatDate(dailySeries[index].date)}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        )}

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="metric-chip">
            <p className="metric-chip-label">Maior entrada diária</p>
            <p className="metric-chip-value text-accent-green">{formatBRL(biggestCreditDay.credits)}</p>
            <p className="mt-2 text-sm text-text-muted">{formatDate(biggestCreditDay.date)}</p>
          </div>
          <div className="metric-chip">
            <p className="metric-chip-label">Maior saída diária</p>
            <p className="metric-chip-value text-accent-red">{formatBRL(biggestDebitDay.debits)}</p>
            <p className="mt-2 text-sm text-text-muted">{formatDate(biggestDebitDay.date)}</p>
          </div>
          <div className="metric-chip">
            <p className="metric-chip-label">Dias no recorte</p>
            <p className="metric-chip-value">{dailySeries.length.toLocaleString('pt-BR')}</p>
            <p className="mt-2 text-sm text-text-muted">{summary.total.toLocaleString('pt-BR')} movimentos visíveis</p>
          </div>
        </div>
      </article>

      <div className="grid gap-4">
        <article className="panel p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="section-kicker">Distribuição</p>
              <h3 className="mt-2 font-display text-[1.8rem] text-text-primary">Volume por banco</h3>
            </div>
            <span className="badge-muted">{bankSeries.length} origens</span>
          </div>

          <div className="mt-5 space-y-4">
            {bankSeries.slice(0, 6).map(item => (
              <div key={item.bank}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-text-primary">{BANK_LABELS[item.bank] || item.bank}</p>
                    <p className="text-xs text-text-muted">{item.count} movimentos</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-text-primary">{formatBRL(item.volume)}</p>
                    <p className={`text-xs ${item.net >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                      saldo {formatBRL(item.net)}
                    </p>
                  </div>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className={item.net >= 0 ? 'h-full rounded-full bg-accent-blue' : 'h-full rounded-full bg-brand-amber'}
                    style={{ width: `${(item.volume / maxBankVolume) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel-soft p-5">
          <p className="section-kicker">Mix</p>
          <h3 className="mt-2 font-display text-[1.8rem] text-text-primary">Composição do recorte</h3>

          <div className="mt-5 space-y-5">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="label-muted">Créditos x débitos</p>
                <p className="text-sm text-text-secondary">{formatBRL(summary.volume)} em volume</p>
              </div>
              <SegmentedBar segments={movementSegments} />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="label-muted">Extrato x fatura</p>
                <p className="text-sm text-text-secondary">{summary.total.toLocaleString('pt-BR')} movimentos</p>
              </div>
              <SegmentedBar segments={docTypeSegments} />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="metric-chip">
                <p className="metric-chip-label">Ticket médio</p>
                <p className="metric-chip-value">{formatBRL(summary.averageTicket)}</p>
              </div>
              <div className="metric-chip">
                <p className="metric-chip-label">Saldo líquido</p>
                <p className={`metric-chip-value ${summary.net >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                  {formatBRL(summary.net)}
                </p>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>
  )
}
