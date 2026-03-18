import tempfile
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models import ParseResultSchema
from backend.parsers import detect_and_parse, to_json
from backend.ofx.generator import generate_ofx

app = FastAPI(title="OFX_TOP Parser API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/parse", response_model=list[ParseResultSchema])
async def parse_pdfs(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, detail=f"Arquivo não é PDF: {file.filename}")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            txs, bank, metadata = detect_and_parse(tmp_path)
            result = to_json(txs, bank, file.filename, metadata)
            results.append(result)
        except ValueError as e:
            raise HTTPException(400, detail=str(e))
        except Exception as e:
            raise HTTPException(500, detail=f"Erro ao processar {file.filename}: {str(e)}")
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    return results


@app.post("/export-ofx")
async def export_ofx(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, detail=f"Arquivo não é PDF: {file.filename}")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            txs, bank, metadata = detect_and_parse(tmp_path)
            parse_json = to_json(txs, bank, file.filename, metadata)
            ofx_str = generate_ofx(parse_json)
            ofx_filename = file.filename.rsplit('.', 1)[0] + ".ofx"
            results.append({"filename": ofx_filename, "content": ofx_str})
        except ValueError as e:
            raise HTTPException(400, detail=str(e))
        except Exception as e:
            raise HTTPException(500, detail=f"Erro ao processar {file.filename}: {str(e)}")
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    return results