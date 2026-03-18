import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import fs from 'fs'
import { app } from 'electron'

const PYTHON_PORT = 8199
const HEALTH_URL = `http://127.0.0.1:${PYTHON_PORT}/health`
const PARSE_URL = `http://127.0.0.1:${PYTHON_PORT}/parse`
const EXPORT_OFX_URL = `http://127.0.0.1:${PYTHON_PORT}/export-ofx`

let pythonProcess: ChildProcess | null = null

export async function startPythonBackend(): Promise<void> {
  if (app.isPackaged) {
    // Packaged mode: launch the PyInstaller-frozen backend executable
    const backendExe = path.join(process.resourcesPath, 'backend', 'backend_server.exe')
    console.log(`[python-bridge] Starting packaged backend: ${backendExe}`)

    pythonProcess = spawn(backendExe, [], {
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true
    })
  } else {
    // Dev mode: use system Python with uvicorn module
    const pythonExe = process.platform === 'win32' ? 'python' : 'python3'
    const cwd = path.join(__dirname, '..', '..', '..')

    console.log(`[python-bridge] Starting dev backend: ${pythonExe} -m uvicorn backend.main:app --host 127.0.0.1 --port ${PYTHON_PORT}`)

    pythonProcess = spawn(pythonExe, [
      '-m', 'uvicorn', 'backend.main:app',
      '--host', '127.0.0.1',
      '--port', String(PYTHON_PORT),
      '--log-level', 'warning'
    ], {
      cwd,
      stdio: ['ignore', 'pipe', 'pipe']
    })
  }

  pythonProcess.stdout?.on('data', (data) => {
    console.log(`[python] ${data.toString().trim()}`)
  })

  pythonProcess.stderr?.on('data', (data) => {
    const msg = data.toString().trim()
    if (msg.includes('Skipping data after last boundary') || msg.includes('Could not get FontBBox')) return
    console.log(`[python-err] ${msg}`)
  })

  pythonProcess.on('error', (err) => {
    console.error(`[python-bridge] Failed to start: ${err.message}`)
  })

  pythonProcess.on('exit', (code) => {
    console.log(`[python-bridge] Process exited with code ${code}`)
    pythonProcess = null
  })

  await waitForHealth(20000)
}

async function waitForHealth(timeoutMs: number): Promise<void> {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(HEALTH_URL)
      if (res.ok) {
        console.log('[python-bridge] Backend is ready')
        return
      }
    } catch {
      // Backend not ready yet
    }
    await new Promise(r => setTimeout(r, 300))
  }
  throw new Error('Python backend failed to start within timeout')
}

export async function parseFiles(filePaths: string[]): Promise<unknown[]> {
  const FormData = (await import('form-data')).default
  const fetch = (await import('node-fetch')).default

  const formData = new FormData()
  for (const fp of filePaths) {
    formData.append('files', fs.createReadStream(fp), path.basename(fp))
  }

  const res = await fetch(PARSE_URL, {
    method: 'POST',
    body: formData,
    headers: formData.getHeaders()
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Parse failed (${res.status}): ${text}`)
  }

  return res.json() as Promise<unknown[]>
}

export async function exportOFX(filePaths: string[]): Promise<{ filename: string; content: string }[]> {
  const FormData = (await import('form-data')).default
  const fetch = (await import('node-fetch')).default

  const formData = new FormData()
  for (const fp of filePaths) {
    formData.append('files', fs.createReadStream(fp), path.basename(fp))
  }

  const res = await fetch(EXPORT_OFX_URL, {
    method: 'POST',
    body: formData,
    headers: formData.getHeaders()
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Export OFX failed (${res.status}): ${text}`)
  }

  return res.json() as Promise<{ filename: string; content: string }[]>
}

export function stopPythonBackend(): void {
  if (pythonProcess && pythonProcess.pid) {
    console.log('[python-bridge] Stopping backend...')
    // On Windows, kill the entire process tree to ensure uvicorn workers also terminate
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(pythonProcess.pid), '/f', '/t'])
    } else {
      pythonProcess.kill()
    }
    pythonProcess = null
  }
}