import type { SummaryMetrics } from '../types'

interface SummaryCardProps {
  summary: SummaryMetrics
}

function formatBRL(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export default function SummaryCard({ summary }: SummaryCardProps) {
  const debitVolume = Math.abs(summary.debits)
  const cards = [
    {
      label: 'Transações',
      value: summary.total.toLocaleString('pt-BR'),
      description: `ticket médio ${formatBRL(summary.averageTicket)}`,
      tone: 'text-text-primary',
      accent: 'bg-brand-amber',
    },
    {
      label: 'Volume',
      value: formatBRL(summary.volume),
      description: 'soma absoluta do recorte',
      tone: 'text-text-primary',
      accent: 'bg-brand-amber',
    },
    {
      label: 'Créditos',
      value: formatBRL(summary.credits),
      description: `${summary.volume > 0 ? Math.round((summary.credits / summary.volume) * 100) : 0}% do volume`,
      tone: 'text-accent-green',
      accent: 'bg-accent-green',
    },
    {
      label: 'Débitos',
      value: formatBRL(debitVolume),
      description: `${summary.volume > 0 ? Math.round((debitVolume / summary.volume) * 100) : 0}% do volume`,
      tone: 'text-accent-red',
      accent: 'bg-accent-red',
    },
  ]

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {cards.map(card => (
        <article key={card.label} className="panel overflow-hidden p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="label-muted">{card.label}</p>
              <p className={`mt-3 font-display text-[2rem] leading-none ${card.tone}`}>{card.value}</p>
            </div>
            <span className={`mt-1 h-2.5 w-2.5 rounded-full ${card.accent}`} />
          </div>

        </article>
      ))}
    </section>
  )
}
