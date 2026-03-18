"""CLI: python -m backend.cli [--ofx] [--json] arquivo.pdf [arquivo2.pdf ...]"""
import sys
import json
from pathlib import Path

from backend.parsers import detect_and_parse, to_json
from backend.ofx.generator import generate_ofx


def main():
    args = sys.argv[1:]
    if not args:
        print("Uso: python -m backend.cli [--ofx] [--json] arquivo.pdf [arquivo2.pdf ...]")
        sys.exit(1)

    do_ofx = "--ofx" in args
    do_json = "--json" in args
    pdf_files = [a for a in args if not a.startswith("--")]

    if not do_ofx and not do_json:
        do_json = True

    if not pdf_files:
        print("Nenhum arquivo PDF informado.")
        sys.exit(1)

    for pdf_file in pdf_files:
        print(f"\nProcessando: {pdf_file}")
        try:
            txs, bank, metadata = detect_and_parse(pdf_file)
            out = to_json(txs, bank, pdf_file, metadata)

            if do_json:
                out_path = Path(pdf_file).with_suffix(".json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False, indent=2)
                print(f"  Banco: {bank} | Transações: {len(txs)} | JSON: {out_path}")

            if do_ofx:
                ofx_str = generate_ofx(out)
                ofx_path = Path(pdf_file).with_suffix(".ofx")
                with open(ofx_path, "w", encoding="utf-8") as f:
                    f.write(ofx_str)
                print(f"  Banco: {bank} | Transações: {len(txs)} | OFX: {ofx_path}")

        except Exception as e:
            print(f"  ERRO: {e}")
            raise


if __name__ == "__main__":
    main()
