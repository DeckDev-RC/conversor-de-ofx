import { useState, useEffect, type Dispatch, type SetStateAction } from 'react'

interface Filters {
  search: string
  bank: string
  docType: string
  amountType: string
  dateFrom: string
  dateTo: string
}

interface FilterBarProps {
  filters: Filters
  setFilters: Dispatch<SetStateAction<Filters>>
  banks: string[]
}

const BANK_LABELS: Record<string, string> = {
  xp_extrato: 'XP',
  itau_extrato: 'Itau',
  stone_extrato: 'Stone',
  brb_extrato: 'BRB Extrato',
  brb_fatura: 'BRB Fatura',
  sicoob_extrato: 'Sicoob Extrato',
  sicoob_fatura: 'Sicoob Fatura',
  bradesco_extrato: 'Bradesco',
}

function MaskedDateInput({ value, onChange, placeholder, title }: { value: string, onChange: (v: string) => void, placeholder: string, title: string }) {
  const [display, setDisplay] = useState('')

  useEffect(() => {
    if (!value) {
      setDisplay('')
      return
    }
    const parts = value.split('-')
    if (parts.length === 3) {
      const expectedRaw = `${parts[2]}${parts[1]}${parts[0]}`
      setDisplay((prev) => {
        const currentRaw = prev.replace(/\D/g, '')
        if (currentRaw !== expectedRaw) {
          return `${parts[2]}/${parts[1]}/${parts[0]}`
        }
        return prev
      })
    }
  }, [value])

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    let raw = e.target.value.replace(/\D/g, '')
    if (raw.length > 8) raw = raw.slice(0, 8)
    
    let formatted = raw
    if (raw.length > 2) {
      formatted = `${raw.slice(0, 2)}/${raw.slice(2, 4)}`
      if (raw.length > 4) {
        formatted += `/${raw.slice(4)}`
      }
    }
    setDisplay(formatted)

    if (raw.length === 8) {
      const year = raw.slice(4)
      const month = raw.slice(2, 4)
      const day = raw.slice(0, 2)
      if (parseInt(month) <= 12 && parseInt(day) <= 31) {
        onChange(`${year}-${month}-${day}`)
      }
    } else if (raw.length === 0) {
      onChange('')
    }
  }

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)
  }

  return (
    <div className="relative w-full flex items-center group">
      <input
        type="text"
        placeholder={placeholder}
        value={display}
        onChange={handleInput}
        className="input-dark w-full pr-10"
        title={title}
      />
      <div className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 rounded-md flex items-center justify-center overflow-hidden hover:bg-white/[0.04] transition-colors">
        <svg className="pointer-events-none absolute h-4 w-4 text-text-muted transition-colors group-hover:text-brand-amber/90" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <input
          type="date"
          value={value}
          onChange={handleDateChange}
          onClick={(e) => {
            try { (e.target as HTMLInputElement).showPicker() } catch (err) {}
          }}
          className="absolute inset-0 opacity-0 cursor-pointer w-full h-full [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:inset-0 [&::-webkit-calendar-picker-indicator]:w-full [&::-webkit-calendar-picker-indicator]:h-full [&::-webkit-calendar-picker-indicator]:opacity-0 [&::-webkit-calendar-picker-indicator]:cursor-pointer"
        />
      </div>
    </div>
  )
}

export default function FilterBar({ filters, setFilters, banks }: FilterBarProps) {
  const update = (key: keyof Filters, value: string) => {
    setFilters(previous => ({ ...previous, [key]: value }))
  }

  const activeFilters = Object.values(filters).filter(value => value !== '').length
  const hasFilters = activeFilters > 0

  return (
    <section className="panel p-5 lg:p-6">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          {hasFilters && <span className="badge-muted">{activeFilters} filtros ativos</span>}
        </div>

        {hasFilters && (
          <button
            onClick={() => setFilters({ search: '', bank: '', docType: '', amountType: '', dateFrom: '', dateTo: '' })}
            className="btn-secondary whitespace-nowrap"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Limpar filtros
          </button>
        )}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-12">
        <div className="xl:col-span-3">
          <label className="label-muted">Busca</label>
          <div className="relative mt-2">
            <svg className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Buscar descrição ou memo"
              value={filters.search}
              onChange={event => update('search', event.target.value)}
              className="input-dark w-full pl-9"
            />
          </div>
        </div>

        <div className="xl:col-span-2">
          <label className="label-muted">Banco</label>
          <select value={filters.bank} onChange={event => update('bank', event.target.value)} className="input-dark mt-2 w-full">
            <option value="">Todos os bancos</option>
            {banks.map(bank => (
              <option key={bank} value={bank}>
                {BANK_LABELS[bank] || bank}
              </option>
            ))}
          </select>
        </div>

        <div className="xl:col-span-2">
          <label className="label-muted">Documento</label>
          <select value={filters.docType} onChange={event => update('docType', event.target.value)} className="input-dark mt-2 w-full">
            <option value="">Todos os tipos</option>
            <option value="checking">Extrato</option>
            <option value="creditcard">Fatura</option>
          </select>
        </div>

        <div className="xl:col-span-2">
          <label className="label-muted">Natureza</label>
          <select value={filters.amountType} onChange={event => update('amountType', event.target.value)} className="input-dark mt-2 w-full">
            <option value="">Débito e crédito</option>
            <option value="credit">Créditos</option>
            <option value="debit">Débitos</option>
          </select>
        </div>

        <div className="xl:col-span-3">
          <label className="label-muted">Período</label>
          <div className="mt-2 flex items-center gap-2">
            <MaskedDateInput
              placeholder="DD/MM/AAAA"
              value={filters.dateFrom}
              onChange={val => update('dateFrom', val)}
              title="Data inicial"
            />
            <span className="text-text-muted text-sm">-</span>
            <MaskedDateInput
              placeholder="DD/MM/AAAA"
              value={filters.dateTo}
              onChange={val => update('dateTo', val)}
              title="Data final"
            />
          </div>
        </div>
      </div>
    </section>
  )
}
