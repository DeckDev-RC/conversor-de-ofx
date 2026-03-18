import { useCallback, useState, type DragEvent } from 'react'

interface DropZoneProps {
  isDesktop: boolean
  onFiles: (paths: string[]) => void
  isLoading: boolean
}

const supportedBanks = ['XP', 'Itau', 'Stone', 'BRB', 'Sicoob', 'Bradesco']

export default function DropZone({ isDesktop, onFiles, isLoading }: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const canImport = isDesktop && !isLoading

  const handleDragEnter = useCallback((event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    if (canImport) {
      setIsDragOver(true)
    }
  }, [canImport])

  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    if (canImport) {
      event.dataTransfer.dropEffect = 'copy'
    } else {
      event.dataTransfer.dropEffect = 'none'
    }
  }, [canImport])

  const handleDragLeave = useCallback((event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((event: DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragOver(false)

    if (!canImport) return

    const files = Array.from(event.dataTransfer.files)
    const pdfPaths: string[] = []

    for (const file of files) {
      if (file.name.toLowerCase().endsWith('.pdf')) {
        let path = ''
        if (window.electronAPI && window.electronAPI.getPathForFile) {
           path = window.electronAPI.getPathForFile(file)
        } else {
           path = (file as any).path || ''
        }
        
        if (path) {
          pdfPaths.push(path)
        }
      }
    }

    if (pdfPaths.length > 0) {
      onFiles(pdfPaths)
    }
  }, [canImport, onFiles])

  const handleBrowse = useCallback(async () => {
    if (!window.electronAPI || isLoading) return
    const paths = await window.electronAPI.selectFiles()
    if (paths.length > 0) {
      onFiles(paths)
    }
  }, [isLoading, onFiles])

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => canImport && void handleBrowse()}
      className={`group relative overflow-hidden rounded-nf-xl transition-all duration-300 ease-apple ${canImport ? 'cursor-pointer' : ''} ${isLoading ? 'opacity-70' : ''} ${isDragOver ? 'scale-[1.005]' : ''}`}
      style={{
        borderColor: isDragOver ? 'rgba(229, 187, 120, 0.42)' : undefined,
      }}
    >
      {/* Dashed drop area */}
      <div
        className={`rounded-nf-xl border-2 border-dashed transition-all duration-300 ${
          isDragOver
            ? 'border-brand-amber/50 bg-brand-amber/[0.04]'
            : 'border-white/[0.12] bg-white/[0.02] hover:border-white/[0.2] hover:bg-white/[0.03]'
        }`}
      >
        <div className="flex flex-col items-center justify-center px-6 py-14 lg:py-20">
          {/* Upload icon */}
          <div
            className={`flex h-20 w-20 items-center justify-center rounded-[22px] border transition-all duration-300 ${
              isDragOver
                ? 'border-brand-amber/30 bg-brand-amber/[0.08] shadow-[0_0_40px_rgba(229,187,120,0.15)]'
                : 'border-white/10 bg-white/[0.04] group-hover:border-white/[0.18] group-hover:bg-white/[0.06]'
            }`}
          >
            {isLoading ? (
              <div className="h-9 w-9 rounded-full border-[2.5px] border-brand-amber/20 border-t-brand-amber animate-spin" />
            ) : (
              <svg
                className={`h-9 w-9 transition-all duration-300 ${
                  isDragOver ? 'text-brand-amber -translate-y-1' : 'text-text-muted group-hover:text-text-secondary'
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={1.4}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L8 8m4-4l4 4" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 15v4a2 2 0 002 2h14a2 2 0 002-2v-4" />
              </svg>
            )}
          </div>

          {/* Title */}
          <h2 className="mt-6 font-display text-[1.6rem] tracking-[-0.04em] text-text-primary">
            {isLoading ? 'Processando seus PDFs...' : isDragOver ? 'Solte os arquivos aqui' : 'Arraste PDFs ou clique para selecionar'}
          </h2>

          {/* Subtitle */}
          <p className="mt-2 text-sm text-text-muted">
            {isLoading ? 'Aguarde enquanto os arquivos são processados' : 'Extratos e faturas em PDF dos bancos suportados'}
          </p>

          {/* Bank chips */}
          {!isLoading && (
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {supportedBanks.map(bank => (
                <span key={bank} className="badge-muted">
                  {bank}
                </span>
              ))}
            </div>
          )}

          {/* CTA button */}
          {!isLoading && (
            <button
              onClick={event => {
                event.stopPropagation()
                if (canImport) {
                  void handleBrowse()
                }
              }}
              disabled={!canImport}
              className="btn-primary mt-8"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m0 0l-6-6m6 6l6-6" />
              </svg>
              {isDesktop ? 'Selecionar PDFs' : 'Abrir no desktop'}
            </button>
          )}

          {/* Formats hint */}
          {!isLoading && (
            <p className="mt-5 text-xs text-text-disabled">
              Saída em JSON ou OFX
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
