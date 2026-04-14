#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from app_version import APP_NAME, APP_VERSION
from georef_pipeline import analyze_input_file, copy_input_to_output, geocode_csv


ALLOWED_SUFFIXES = {".xlsx", ".xlsm", ".csv"}
ANALYSIS_WEIGHT = 0.14
GEOCODING_WEIGHT = 0.81
PACKAGING_WEIGHT = 0.05
JOB_TTL_SECONDS = 60 * 60

app = Flask(__name__)
jobs_lock = threading.Lock()
jobs: dict[str, dict[str, Any]] = {}


def now_ts() -> float:
    return time.time()


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_SUFFIXES


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def build_zip_file(folder: Path, destination: Path) -> Path:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(folder))
    return destination


def render_home(error: str | None = None) -> str:
    return render_template(
        "index.html",
        error=error,
        app_name=APP_NAME,
        app_version=APP_VERSION,
    )


def purge_old_jobs() -> None:
    cutoff = now_ts() - JOB_TTL_SECONDS
    removable: list[str] = []
    with jobs_lock:
        for job_id, job in jobs.items():
            finished_at = job.get("finished_at")
            if finished_at is not None and finished_at < cutoff:
                removable.append(job_id)

        for job_id in removable:
            job = jobs.pop(job_id)
            temp_dir = job.get("_temp_dir")
            if temp_dir is not None:
                temp_dir.cleanup()


def update_job(job_id: str, **changes: Any) -> None:
    with jobs_lock:
        job = jobs[job_id]
        job.update(changes)
        job["updated_at"] = now_ts()


def get_job(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job.copy()


def serialize_job(job: dict[str, Any]) -> dict[str, Any]:
    now = now_ts()
    started_at = job.get("started_at")
    elapsed_seconds = None
    if started_at is not None:
        elapsed_seconds = max(0, round(now - started_at))

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "stage": job["stage"],
        "message": job["message"],
        "progress": job["progress"],
        "progress_percent": round(job["progress"] * 100),
        "eta_seconds": job.get("eta_seconds"),
        "elapsed_seconds": elapsed_seconds,
        "input_file": job.get("input_file"),
        "dry_run": job.get("dry_run", False),
        "analysis_counts": job.get("analysis_counts"),
        "geocoding": job.get("geocoding"),
        "download_url": job.get("download_url"),
        "archive_name": job.get("archive_name"),
        "error": job.get("error"),
    }


def write_job_manifest(
    output_dir: Path,
    *,
    input_path: Path,
    dry_run: bool,
    analysis_counts: dict[str, int],
    geocode: dict[str, Any],
) -> None:
    manifest = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "input_file": input_path.name,
        "dry_run": dry_run,
        "analysis": analysis_counts,
        "geocoding": to_jsonable(geocode),
    }
    (output_dir / "job_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def process_job(job_id: str) -> None:
    with jobs_lock:
        job = jobs[job_id]
        temp_dir = Path(job["temp_dir_path"])
        input_path = Path(job["input_path"])
        output_dir = Path(job["output_dir"])
        dry_run = bool(job["dry_run"])
        email = job.get("email")

    try:
        update_job(
            job_id,
            status="running",
            stage="analysis",
            progress=0.04,
            message="Analisi del file in corso",
            eta_seconds=None,
            started_at=now_ts(),
        )
        analysis = analyze_input_file(input_path, output_dir)
        analysis_counts = {
            category: len(records)
            for category, records in analysis["categories"].items()
        }
        valid_count = analysis_counts.get("validi", 0)
        update_job(
            job_id,
            stage="analysis_complete",
            progress=ANALYSIS_WEIGHT,
            message=f"Analisi completata: {valid_count} indirizzi validi da geocodificare",
            analysis_counts=analysis_counts,
            geocoding={
                "current": 0,
                "total": valid_count,
                "matched": 0,
                "not_found": 0,
                "last_address": None,
                "last_status": None,
            },
        )

        geocoded_csv = output_dir / f"{input_path.stem}_validi_geocoded.csv"
        cache_path = output_dir / "nominatim_cache.json"
        geocode_started = now_ts()

        def progress_callback(current: int, total: int, address: str, status: str) -> None:
            if total <= 0:
                progress = ANALYSIS_WEIGHT + GEOCODING_WEIGHT
                eta_seconds = 0
            else:
                progress = ANALYSIS_WEIGHT + GEOCODING_WEIGHT * (current / total)
                eta_seconds = None
                if current > 0:
                    elapsed = max(0.1, now_ts() - geocode_started)
                    eta_seconds = max(0, round((elapsed / current) * (total - current)))

            update_job(
                job_id,
                stage="geocoding",
                progress=progress,
                eta_seconds=eta_seconds,
                message=f"Geocodifica in corso: {current}/{total}",
                geocoding={
                    "current": current,
                    "total": total,
                    "matched": None,
                    "not_found": None,
                    "last_address": address,
                    "last_status": status,
                },
            )

        update_job(
            job_id,
            stage="geocoding",
            progress=ANALYSIS_WEIGHT,
            message="Geocodifica degli indirizzi validi in corso",
            eta_seconds=None,
        )
        geocode = geocode_csv(
            analysis["paths"]["validi"],
            geocoded_csv,
            cache_path=cache_path,
            email=email,
            user_agent="PuliziaDatiSinergia-Web/1.0 (+local-webapp)",
            dry_run=dry_run,
            progress_callback=progress_callback,
        )

        update_job(
            job_id,
            stage="packaging",
            progress=1.0 - PACKAGING_WEIGHT,
            message="Preparazione archivio ZIP finale",
            eta_seconds=1,
            geocoding={
                "current": geocode["rows"],
                "total": geocode["rows"],
                "matched": geocode["matched"],
                "not_found": geocode["not_found"],
                "last_address": None,
                "last_status": None,
            },
        )

        copy_input_to_output(input_path, output_dir)
        write_job_manifest(
            output_dir,
            input_path=input_path,
            dry_run=dry_run,
            analysis_counts=analysis_counts,
            geocode=geocode,
        )
        archive_name = f"{input_path.stem}_risultati.zip"
        archive_path = temp_dir / archive_name
        build_zip_file(output_dir, archive_path)

        update_job(
            job_id,
            status="completed",
            stage="completed",
            progress=1.0,
            message="Elaborazione completata. ZIP pronto da scaricare.",
            eta_seconds=0,
            finished_at=now_ts(),
            archive_name=archive_name,
            archive_path=str(archive_path),
            download_url=f"/download/{job_id}",
        )
    except Exception as exc:
        update_job(
            job_id,
            status="error",
            stage="error",
            progress=0.0,
            message="Errore durante l'elaborazione",
            error=str(exc),
            eta_seconds=None,
            finished_at=now_ts(),
        )


def create_background_job(uploaded_file, email: str | None, dry_run: bool) -> dict[str, Any]:
    purge_old_jobs()
    safe_name = secure_filename(uploaded_file.filename) or "input_file"
    temp_dir = tempfile.TemporaryDirectory(prefix="pulizia-dati-")
    temp_path = Path(temp_dir.name)
    input_path = temp_path / safe_name
    output_dir = temp_path / "output"
    uploaded_file.save(input_path)

    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0.0,
        "message": "Upload ricevuto, avvio elaborazione",
        "eta_seconds": None,
        "error": None,
        "input_file": safe_name,
        "email": email,
        "dry_run": dry_run,
        "analysis_counts": None,
        "geocoding": None,
        "archive_name": None,
        "archive_path": None,
        "download_url": None,
        "created_at": now_ts(),
        "started_at": None,
        "updated_at": now_ts(),
        "finished_at": None,
        "temp_dir_path": str(temp_path),
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "_temp_dir": temp_dir,
    }

    with jobs_lock:
        jobs[job_id] = job

    worker = threading.Thread(target=process_job, args=(job_id,), daemon=True)
    worker.start()
    return serialize_job(job)


@app.get("/")
def index() -> str:
    return render_home()


@app.post("/api/jobs")
def start_job():
    uploaded_file = request.files.get("source_file")
    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "Seleziona un file Excel o CSV da elaborare."}), 400

    if not allowed_file(uploaded_file.filename):
        return jsonify({"error": "Formato non supportato. Carica un file .xlsx, .xlsm oppure .csv."}), 400

    email = request.form.get("email", "").strip() or None
    dry_run = request.form.get("dry_run") == "on"
    job = create_background_job(uploaded_file, email=email, dry_run=dry_run)
    return jsonify(job), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    try:
        job = get_job(job_id)
    except KeyError:
        abort(404)
    return jsonify(serialize_job(job))


@app.get("/download/<job_id>")
def download_result(job_id: str):
    try:
        job = get_job(job_id)
    except KeyError:
        abort(404)

    if job["status"] != "completed" or not job.get("archive_path"):
        return jsonify({"error": "Archivio non ancora disponibile."}), 409

    return send_file(
        job["archive_path"],
        mimetype="application/zip",
        as_attachment=True,
        download_name=job["archive_name"],
    )


@app.post("/process")
def process_upload():
    uploaded_file = request.files.get("source_file")
    if uploaded_file is None or uploaded_file.filename == "":
        return render_home("Seleziona un file Excel o CSV da elaborare."), 400
    return render_home(
        "Questa schermata ora usa l'elaborazione asincrona. Invia il file dalla home e attendi il completamento."
    )


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    app.run(host=host, port=port, debug=False, threaded=True)
