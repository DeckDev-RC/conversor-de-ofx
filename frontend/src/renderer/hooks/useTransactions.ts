import { useState, useMemo } from 'react'
import type { SortField, SortDirection, SummaryMetrics, TransactionRecord } from '../types'

interface Filters {
  search: string
  bank: string
  docType: string
  amountType: string
  dateFrom: string
  dateTo: string
}

export function useTransactions(transactions: TransactionRecord[]) {
  const [filters, setFilters] = useState<Filters>({
    search: '',
    bank: '',
    docType: '',
    amountType: '',
    dateFrom: '',
    dateTo: '',
  })
  const [sortField, setSortField] = useState<SortField>('date')
  const [sortDir, setSortDir] = useState<SortDirection>('desc')

  const banks = useMemo(() => {
    const set = new Set(transactions.map(t => t._bank))
    return Array.from(set).sort()
  }, [transactions])

  const filtered = useMemo(() => {
    let result = [...transactions]

    if (filters.search) {
      const q = filters.search.toLowerCase()
      result = result.filter(t =>
        t.description.toLowerCase().includes(q) ||
        t.memo.toLowerCase().includes(q)
      )
    }

    if (filters.bank) {
      result = result.filter(t => t._bank === filters.bank)
    }

    if (filters.docType) {
      result = result.filter(t => t.doc_type === filters.docType)
    }

    if (filters.amountType === 'credit') {
      result = result.filter(t => t.amount > 0)
    } else if (filters.amountType === 'debit') {
      result = result.filter(t => t.amount < 0)
    }

    if (filters.dateFrom) {
      result = result.filter(t => t.date >= filters.dateFrom)
    }

    if (filters.dateTo) {
      result = result.filter(t => t.date <= filters.dateTo)
    }

    // Sort
    result.sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'date':
          cmp = a.date.localeCompare(b.date)
          break
        case 'description':
          cmp = a.description.localeCompare(b.description)
          break
        case 'amount':
          cmp = a.amount - b.amount
          break
        case 'bank':
          cmp = a._bank.localeCompare(b._bank)
          break
        case 'doc_type':
          cmp = a.doc_type.localeCompare(b.doc_type)
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })

    return result
  }, [transactions, filters, sortField, sortDir])

  const summary = useMemo<SummaryMetrics>(() => {
    const credits = filtered.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0)
    const debits = filtered.filter(t => t.amount < 0).reduce((s, t) => s + t.amount, 0)
    const volume = filtered.reduce((sum, transaction) => sum + Math.abs(transaction.amount), 0)
    return {
      total: filtered.length,
      credits,
      debits,
      net: credits + debits,
      volume,
      averageTicket: filtered.length > 0 ? volume / filtered.length : 0,
    }
  }, [filtered])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('asc')
    }
  }

  return { filtered, filters, setFilters, banks, summary, sortField, sortDir, toggleSort }
}
