#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from georef_pipeline import copy_input_to_output, run_full_pipeline


ALLOWED_SUFFIXES = {".xlsx", ".xlsm", ".csv"}

app = Flask(__name__)


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_SUFFIXES


def build_zip_bytes(folder: Path) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(folder))
    buffer.seek(0)
    return buffer


def to_jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def render_home(error: str | None = None) -> str:
    return render_template("index.html", error=error)


@app.get("/")
def index() -> str:
    return render_home()


@app.post("/process")
def process_upload():
    uploaded_file = request.files.get("source_file")
    if uploaded_file is None or uploaded_file.filename == "":
        return render_home("Seleziona un file Excel o CSV da elaborare."), 400

    if not allowed_file(uploaded_file.filename):
        return render_home("Formato non supportato. Carica un file .xlsx, .xlsm oppure .csv."), 400

    email = request.form.get("email", "").strip() or None
    dry_run = request.form.get("dry_run") == "on"

    safe_name = secure_filename(uploaded_file.filename) or "input_file"
    with tempfile.TemporaryDirectory(prefix="pulizia-dati-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        input_path = temp_dir / safe_name
        output_dir = temp_dir / "output"
        uploaded_file.save(input_path)

        try:
            pipeline = run_full_pipeline(
                input_path,
                output_dir,
                geocoder_email=email,
                user_agent="PuliziaDatiSinergia-Web/1.0 (+local-webapp)",
                dry_run=dry_run,
            )
        except Exception as exc:
            return render_home(f"Errore durante l'elaborazione: {exc}"), 500

        copy_input_to_output(input_path, output_dir)
        manifest = {
            "input_file": input_path.name,
            "dry_run": dry_run,
            "analysis": {
                category: len(records)
                for category, records in pipeline["categories"].items()
            },
            "geocoding": to_jsonable(pipeline["geocode"]),
        }
        (output_dir / "job_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        zip_buffer = build_zip_bytes(output_dir)
        archive_name = f"{input_path.stem}_risultati.zip"
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=archive_name,
        )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
