import { useState, useCallback, useRef } from 'react'
import type { ParsedFile, ParseResult } from '../types'

export function useParseFiles(initialFiles: ParsedFile[] = []) {
  const initialFilesRef = useRef(initialFiles)
  const [files, setFiles] = useState<ParsedFile[]>(initialFiles)
  const [isLoading, setIsLoading] = useState(false)

  const addFiles = useCallback(async (filePaths: string[]) => {
    const newFiles: ParsedFile[] = filePaths.map(p => ({
      name: p.split(/[\\/]/).pop() || p,
      path: p,
      status: 'pending' as const,
    }))

    setFiles(prev => [...prev, ...newFiles])
    setIsLoading(true)

    // Mark all as parsing
    setFiles(prev =>
      prev.map(f =>
        newFiles.some(nf => nf.path === f.path) ? { ...f, status: 'parsing' as const } : f
      )
    )

    try {
      const results: ParseResult[] = await window.electronAPI.parseFiles(filePaths)

      setFiles(prev =>
        prev.map(f => {
          const result = results.find(r => r.source === f.name)
          if (result) {
            return { ...f, status: 'done' as const, result }
          }
          if (newFiles.some(nf => nf.path === f.path) && f.status === 'parsing') {
            return { ...f, status: 'error' as const, error: 'Sem resultado retornado' }
          }
          return f
        })
      )
    } catch (err) {
      setFiles(prev =>
        prev.map(f =>
          f.status === 'parsing'
            ? { ...f, status: 'error' as const, error: err instanceof Error ? err.message : String(err) }
            : f
        )
      )
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearFiles = useCallback(() => {
    if (!window.electronAPI && initialFilesRef.current.length > 0) {
      setFiles(initialFilesRef.current)
      return
    }
    setFiles([])
  }, [])

  const allTransactions = files
    .filter(f => f.status === 'done' && f.result)
    .flatMap(f => f.result!.transactions.map(t => ({ ...t, _bank: f.result!.bank, _source: f.result!.source })))

  return { files, addFiles, clearFiles, allTransactions, isLoading }
}
