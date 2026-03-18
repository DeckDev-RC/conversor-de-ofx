### OFX TOP

App desktop (Electron + React) para **parsear extratos/faturas em PDF** e exportar **JSON** e **OFX v1.02** (foco em importação no Conta Azul).

### Stack

- **Frontend**: Electron + React + Vite (`frontend/`)
- **Backend**: FastAPI (`backend/`)
- **Build Windows**: PyInstaller (backend) + electron-builder (installer)

### Estrutura do repositório

- `frontend/`: app Electron (UI + IPC + empacotamento)
- `backend/`: API FastAPI + parsers + gerador OFX + CLI
- `sample_pdfs/`: PDFs de exemplo (fixtures)
- `artifacts/`: saídas geradas (ignorado no git)
- `backend_dist/`: distribuição do backend empacotado (ignorado no git)
- `build.bat`: build completo “one-shot” (Windows)

### Requisitos

- **Windows 10/11**
- **Node.js** (recomendado LTS)
- **Python 3.11+** (recomendado)

### Rodar em desenvolvimento (backend)

Instalar dependências:

```bash
python -m pip install -r backend/requirements.txt
```

Subir a API (porta padrão **8199**):

```bash
python backend/run_server.py
```

Variáveis de ambiente:

- **`PORT`**: porta do backend (default: `8199`)

Endpoints:

- `GET /health` → status
- `POST /parse` → recebe PDFs e retorna lista de ParseResults (JSON)
- `POST /export-ofx` → recebe PDFs e retorna `{ filename, content }` (OFX em string)

### Rodar em desenvolvimento (frontend)

```bash
cd frontend
npm install
npm run dev
```

Observação: o frontend espera um backend rodando localmente (ver `backend/run_server.py`).

### CLI (converter PDF para JSON/OFX)

```bash
# JSON (padrão)
python -m backend.cli arquivo.pdf

# OFX
python -m backend.cli --ofx arquivo.pdf

# Ambos
python -m backend.cli --ofx --json arquivo.pdf
```

### Build (Windows) — instalador

O fluxo de build completo está automatizado no `build.bat`:

```bat
build.bat
```

O que ele faz:

- limpa builds anteriores
- gera o backend com **PyInstaller** (`backend/backend_server.spec`)
- copia para `backend_dist/backend_server`
- roda `npm run dist` no `frontend/` (electron-builder) e cria o instalador

Saída esperada:

- **Installer** em `frontend/release/` (ex.: `.exe` do NSIS)

### Notas de versionamento

- O `.gitignore` ignora **artefatos gerados** (`backend/dist`, `backend/build`, `frontend/dist`, `frontend/release`, `backend_dist`, `artifacts`) e **segredos** (`.env*`).

