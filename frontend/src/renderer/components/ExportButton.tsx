import type { ParsedFile } from '../types'

interface ExportButtonProps {
  files: ParsedFile[]
}

export default function ExportButton({ files }: ExportButtonProps) {
  const doneFiles = files.filter(file => file.status === 'done' && file.result)

  if (doneFiles.length === 0) return null

  const handleExportJSON = async () => {
    const data = doneFiles.map(file => file.result!)
    const defaultName = doneFiles.length === 1 ? `${doneFiles[0].name.replace('.pdf', '')}.json` : 'extratos_bancarios.json'

    await window.electronAPI.exportJSON(doneFiles.length === 1 ? data[0] : data, defaultName)
  }

  const handleExportOFX = async () => {
    const filePaths = doneFiles.map(file => file.path)
    await window.electronAPI.exportOFX(filePaths)
  }

  return (
    <div className="flex items-center gap-2">
      <button onClick={handleExportJSON} className="btn-secondary">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        JSON
      </button>
      <button onClick={handleExportOFX} className="btn-primary">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        OFX
      </button>
    </div>
  )
}
