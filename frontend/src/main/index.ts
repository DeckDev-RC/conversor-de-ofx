import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import path from 'path'
import fs from 'fs'
import { startPythonBackend, parseFiles, exportOFX, stopPythonBackend } from './python-bridge'

let mainWindow: BrowserWindow | null = null

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'OFX TOP',
    icon: path.join(__dirname, '../../build/icon.png'),
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#111111',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('maximize', () => {
    mainWindow?.webContents.send('window-maximized', true)
  })

  mainWindow.on('unmaximize', () => {
    mainWindow?.webContents.send('window-maximized', false)
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'))
  }
}

ipcMain.handle('window-minimize', () => {
  mainWindow?.minimize()
})

ipcMain.handle('window-maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})

ipcMain.handle('window-close', () => {
  mainWindow?.close()
})

ipcMain.handle('window-is-maximized', () => {
  return mainWindow?.isMaximized() ?? false
})

// IPC Handlers
ipcMain.handle('select-files', async () => {
  if (!mainWindow) return []
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Selecionar PDFs Bancários',
    filters: [{ name: 'PDF', extensions: ['pdf'] }],
    properties: ['openFile', 'multiSelections']
  })
  return result.filePaths
})

ipcMain.handle('parse-files', async (_event, filePaths: string[]) => {
  try {
    return await parseFiles(filePaths)
  } catch (err) {
    throw new Error(`Erro ao processar: ${err instanceof Error ? err.message : String(err)}`)
  }
})

ipcMain.handle('export-json', async (_event, data: object, defaultName: string) => {
  if (!mainWindow) return
  const result = await dialog.showSaveDialog(mainWindow, {
    title: 'Exportar JSON',
    defaultPath: defaultName,
    filters: [{ name: 'JSON', extensions: ['json'] }]
  })
  if (!result.canceled && result.filePath) {
    fs.writeFileSync(result.filePath, JSON.stringify(data, null, 2), 'utf-8')
  }
})

ipcMain.handle('export-ofx', async (_event, filePaths: string[]) => {
  if (!mainWindow) return
  try {
    const results = await exportOFX(filePaths)
    const dirResult = await dialog.showOpenDialog(mainWindow, {
      title: 'Selecionar pasta para salvar OFX',
      properties: ['openDirectory']
    })
    if (dirResult.canceled || !dirResult.filePaths.length) return
    const outDir = dirResult.filePaths[0]
    for (const { filename, content } of results) {
      fs.writeFileSync(path.join(outDir, filename), content, 'utf-8')
    }
  } catch (err) {
    throw new Error(`Erro ao exportar OFX: ${err instanceof Error ? err.message : String(err)}`)
  }
})

app.whenReady().then(async () => {
  createWindow()

  mainWindow?.webContents.send('backend-status', 'starting')
  try {
    await startPythonBackend()
    mainWindow?.webContents.send('backend-status', 'ready')
  } catch (err) {
    console.error('Failed to start Python backend:', err)
    mainWindow?.webContents.send('backend-status', 'error')
  }
})

app.on('window-all-closed', () => {
  stopPythonBackend()
  app.quit()
})

app.on('will-quit', () => {
  stopPythonBackend()
})
