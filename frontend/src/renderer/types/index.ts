export interface Transaction {
  date: string
  description: string
  amount: number
  memo: string
  doc_type: 'checking' | 'creditcard'
  raw_type: string
  fitid: string
}

export interface TransactionRecord extends Transaction {
  _bank: string
  _source: string
}

export interface AccountMetadata {
  bankid: string
  branchid: string
  acctid: string
  acct_type: string
  balance: number
  balance_date: string
}

export interface ParseResult {
  source: string
  bank: string
  generated_at: string
  total_transactions: number
  transactions: Transaction[]
  metadata?: AccountMetadata
}

export type FileStatus = 'pending' | 'parsing' | 'done' | 'error'

export interface ParsedFile {
  name: string
  path: string
  status: FileStatus
  result?: ParseResult
  error?: string
}

export interface SummaryMetrics {
  total: number
  credits: number
  debits: number
  net: number
  volume: number
  averageTicket: number
}

export type SortField = 'date' | 'description' | 'amount' | 'bank' | 'doc_type'
export type SortDirection = 'asc' | 'desc'

export interface ElectronAPI {
  parseFiles: (filePaths: string[]) => Promise<ParseResult[]>
  selectFiles: () => Promise<string[]>
  exportJSON: (data: object, defaultName: string) => Promise<void>
  exportOFX: (filePaths: string[]) => Promise<void>
  onBackendStatus: (callback: (status: string) => void) => void
  windowMinimize: () => Promise<void>
  windowMaximize: () => Promise<void>
  windowClose: () => Promise<void>
  windowIsMaximized: () => Promise<boolean>
  onWindowMaximized: (callback: (isMaximized: boolean) => void) => void
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}
