import { useEffect, useState, type CSSProperties, type ReactNode } from 'react'
import ExportButton from './ExportButton'
import type { ParsedFile } from '../types'
import appIcon from '../../assets/Gemini_Generated_Image_abpdniabpdniabpd.png'

type BackendStatus = 'connecting' | 'starting' | 'ready' | 'error'
type TabId = 'import' | 'dashboard'

interface NavbarProps {
  isDesktop: boolean
  backendStatus: BackendStatus
  hasResults: boolean
  files: ParsedFile[]
  activeTab: TabId
  onTabChange: (tab: TabId) => void
  onClear: () => void
}

interface TabDef {
  id: TabId
  label: string
  icon: ReactNode
  disabled?: boolean
}

const noDrag = { WebkitAppRegion: 'no-drag' } as CSSProperties

export default function Navbar({
  isDesktop,
  backendStatus,
  hasResults,
  files,
  activeTab,
  onTabChange,
  onClear,
}: NavbarProps) {
  const [isMaximized, setIsMaximized] = useState(false)

  useEffect(() => {
    if (!isDesktop) return
    window.electronAPI.windowIsMaximized().then(setIsMaximized)
    window.electronAPI.onWindowMaximized(setIsMaximized)
  }, [isDesktop])

  const tabs: TabDef[] = [
    {
      id: 'import',
      label: 'Importar',
      icon: (
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L8 8m4-4l4 4M3 15v4a2 2 0 002 2h14a2 2 0 002-2v-4" />
        </svg>
      ),
    },
    {
      id: 'dashboard',
      label: 'Dashboard',
      disabled: !hasResults,
      icon: (
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z" />
        </svg>
      ),
    },
  ]

  const statusCopy = {
    ready: 'Parser online',
    error: 'Backend offline',
    starting: 'Inicializando',
    connecting: 'Conectando',
  } satisfies Record<BackendStatus, string>

  const statusTone = {
    ready: 'bg-accent-green shadow-[0_0_12px_rgba(135,209,164,0.45)]',
    error: 'bg-accent-red shadow-[0_0_12px_rgba(240,124,98,0.45)]',
    starting: 'bg-accent-yellow shadow-[0_0_12px_rgba(231,201,123,0.4)]',
    connecting: 'bg-accent-yellow shadow-[0_0_12px_rgba(231,201,123,0.4)]',
  } satisfies Record<BackendStatus, string>

  return (
    <nav
      className="relative z-[100] shrink-0 select-none border-b border-white/10 bg-[rgba(6,12,11,0.82)] backdrop-blur-2xl"
      style={isDesktop ? ({ WebkitAppRegion: 'drag' } as CSSProperties) : undefined}
    >
      <div className="mx-auto flex h-[68px] w-full max-w-[1500px] items-center justify-between gap-4 px-4 lg:px-6">
        <div className="flex min-w-0 items-center gap-4" style={noDrag}>
          <div className="flex items-center gap-3 border-r border-white/10 pr-4">
            <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-[14px] border border-white/10 bg-[rgba(255,255,255,0.06)] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
              <img src={appIcon} alt="Logo" className="h-[90%] w-[90%] object-contain drop-shadow-md" />
            </div>
            <div className="min-w-0">
              <p className="truncate font-display text-[1.1rem] leading-none text-text-primary">OFX TOP</p>
            </div>
          </div>

          <div className="hidden items-center gap-1 rounded-nf-pill border border-white/10 bg-white/[0.03] p-1 md:flex">
            {tabs.map(tab => {
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => !tab.disabled && onTabChange(tab.id)}
                  disabled={tab.disabled}
                  className={`nav-tab ${isActive ? 'nav-tab-active' : ''}`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex items-center gap-3" style={noDrag}>
          <div className="hidden items-center gap-2 rounded-nf-pill border border-white/10 bg-white/[0.03] px-3 py-2 md:flex">
            <span className={`status-dot ${isDesktop ? statusTone[backendStatus] : 'bg-brand-amber shadow-[0_0_12px_rgba(229,187,120,0.35)]'}`} />
            <span className="text-xs font-medium text-text-secondary">{isDesktop ? statusCopy[backendStatus] : 'Preview local'}</span>
          </div>

          {hasResults && isDesktop && (
            <>
              <button onClick={onClear} className="btn-ghost hidden sm:inline-flex">
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.86 12.14A2 2 0 0116.14 21H7.86a2 2 0 01-1.99-1.86L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Limpar
              </button>
              <ExportButton files={files} />
            </>
          )}

          {isDesktop && (
            <div className="flex items-center gap-1 rounded-nf-pill border border-white/10 bg-white/[0.03] p-1">
              <button onClick={() => window.electronAPI.windowMinimize()} className="win-control" title="Minimizar">
                <svg className="h-[10px] w-[10px]" viewBox="0 0 10 1">
                  <rect width="10" height="1" fill="currentColor" />
                </svg>
              </button>

              <button onClick={() => window.electronAPI.windowMaximize()} className="win-control" title="Maximizar">
                {isMaximized ? (
                  <svg className="h-[10px] w-[10px]" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth={1}>
                    <rect x="2" y="0.5" width="7.5" height="7.5" rx="0.5" />
                    <rect x="0.5" y="2" width="7.5" height="7.5" rx="0.5" />
                  </svg>
                ) : (
                  <svg className="h-[10px] w-[10px]" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth={1}>
                    <rect x="0.5" y="0.5" width="9" height="9" rx="0.5" />
                  </svg>
                )}
              </button>

              <button onClick={() => window.electronAPI.windowClose()} className="win-control win-control-close" title="Fechar">
                <svg className="h-[10px] w-[10px]" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth={1.2}>
                  <path d="M0 0L10 10M10 0L0 10" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-white/[0.06] px-4 py-2 md:hidden" style={noDrag}>
        <div className="flex items-center gap-2 overflow-auto">
          {tabs.map(tab => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => !tab.disabled && onTabChange(tab.id)}
                disabled={tab.disabled}
                className={`nav-tab shrink-0 ${isActive ? 'nav-tab-active' : ''}`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
