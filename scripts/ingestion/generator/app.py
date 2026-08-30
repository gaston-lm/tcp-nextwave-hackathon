import json
import os
import re
import shutil
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from dataset_generator import (
    audit_csv,
    default_provider_rates,
    generate_csv,
    validate_decline_rules,
    validate_provider_rates,
)
from generation_config import (
    BASELINE_FILENAME,
    COUNTRIES,
    DECLINE_CODE_DETAILS,
    END_DATE,
    MAX_GENERATION_ROWS,
    MERCHANTS,
    N_TRANSACTIONS,
    OUTPUT_FILENAME,
    PROVIDER_IDS,
    START_DATE,
)
from live_stream import LiveStreamController, validate_rows_per_minute

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "index.html"
OUTPUT_PATH = BASE_DIR / OUTPUT_FILENAME
GENERATION_LOCK = threading.Lock()
RESERVED_FILENAMES = {BASELINE_FILENAME}
LIVE_STREAM = LiveStreamController()


def validate_row_count(value):
    if isinstance(value, bool):
        raise ValueError("La cantidad de filas debe ser un número entero")
    try:
        rows = int(value)
    except (TypeError, ValueError):
        raise ValueError("La cantidad de filas debe ser un número entero") from None
    if str(rows) != str(value).strip() and not isinstance(value, int):
        raise ValueError("La cantidad de filas debe ser un número entero")
    if not 1 <= rows <= MAX_GENERATION_ROWS:
        raise ValueError(
            f"La cantidad de filas debe estar entre 1 y {MAX_GENERATION_ROWS}"
        )
    return rows


def validate_csv_filename(value, allow_reserved=False):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("El nombre del CSV es obligatorio")
    filename = value.strip()
    if filename.lower().endswith(".csv"):
        filename = filename[:-4] + ".csv"
    else:
        filename += ".csv"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\.csv", filename):
        raise ValueError("Usá sólo letras, números, punto, guion o guion bajo")
    if not allow_reserved and filename.lower() in RESERVED_FILENAMES:
        raise ValueError("baseline.csv está reservado; elegí otro nombre")
    return filename


def validate_generation_dates(start_value, end_value):
    if not isinstance(start_value, str) or not isinstance(end_value, str):
        raise ValueError("Las fechas y horas inicial y final son obligatorias")
    try:
        start_date = datetime.fromisoformat(start_value)
        end_date = datetime.fromisoformat(end_value)
    except ValueError:
        raise ValueError(
            "Las fechas y horas deben usar un formato ISO válido"
        ) from None
    if start_date.tzinfo is not None or end_date.tzinfo is not None:
        raise ValueError("Las fechas y horas no deben incluir una zona horaria")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", end_value):
        end_date = end_date.replace(hour=23, minute=59, second=59)
    if start_date > end_date:
        raise ValueError("La fecha y hora inicial no puede ser posterior a la final")
    return start_date, end_date


def validate_live_start(value):
    if not isinstance(value, str):
        raise ValueError("La hora inicial de la simulación es obligatoria")
    try:
        start_at = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("La hora inicial debe usar un formato ISO válido") from None
    if start_at.tzinfo is not None:
        raise ValueError("La hora inicial no debe incluir una zona horaria")
    return start_at


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = INDEX_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/config":
            providers = []
            for provider, provider_id in sorted(
                PROVIDER_IDS.items(), key=lambda item: item[1]
            ):
                countries = {}
                for country, country_data in COUNTRIES.items():
                    if provider not in country_data["providers"]:
                        continue
                    countries[country] = {
                        "methods": country_data["providers"][provider],
                        "banks": country_data["banks"],
                        "merchants": [
                            merchant_data["name"]
                            for merchant_data in MERCHANTS.values()
                            if country in merchant_data["country_weights"]
                        ],
                    }
                providers.append(
                    {"name": provider, "id": provider_id, "countries": countries}
                )
            self.send_json(
                200,
                {
                    "rows": N_TRANSACTIONS,
                    "max_rows": MAX_GENERATION_ROWS,
                    "default_filename": OUTPUT_PATH.name,
                    "start_date": START_DATE.isoformat(sep=" "),
                    "end_date": END_DATE.isoformat(sep=" "),
                    "live_start_at": datetime.now()
                    .replace(second=0, microsecond=0)
                    .isoformat(sep=" "),
                    "live_rows_per_minute": 10000,
                    "max_live_rows_per_minute": 10_000,
                    "provider_rates": default_provider_rates(),
                    "decline_codes": [
                        {
                            "code": code,
                            "display_code": f"{code:02d}",
                            "label": details["label"],
                        }
                        for code, details in DECLINE_CODE_DETAILS.items()
                    ],
                    "providers": providers,
                },
            )
            return

        if path == "/api/live/status":
            self.send_json(200, LIVE_STREAM.status())
            return

        if path == "/download":
            query = parse_qs(urlparse(self.path).query)
            try:
                filename = validate_csv_filename(
                    query.get("filename", [OUTPUT_PATH.name])[0],
                    allow_reserved=True,
                )
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
                return
            csv_path = BASE_DIR / filename
            if not csv_path.exists():
                self.send_json(404, {"error": "Todavía no existe el CSV"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition", f'attachment; filename="{filename}"'
            )
            self.send_header("Content-Length", str(csv_path.stat().st_size))
            self.end_headers()
            with csv_path.open("rb") as file:
                shutil.copyfileobj(file, self.wfile, length=1024 * 1024)
            return

        self.send_json(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/live/stop":
            self.send_json(200, LIVE_STREAM.stop())
            return
        if path not in {"/api/generate", "/api/live/start", "/api/live/config"}:
            self.send_json(404, {"error": "Ruta no encontrada"})
            return

        if not GENERATION_LOCK.acquire(blocking=False):
            self.send_json(409, {"error": "Ya hay una generación en curso"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length > 64 * 1024:
                self.send_json(413, {"error": "Solicitud demasiado grande"})
                return
            payload = json.loads(self.rfile.read(content_length) or b"{}")
            if path == "/api/live/config":
                provider_rates = validate_provider_rates(payload.get("provider_rates"))
                rules = validate_decline_rules(payload.get("rules", []), provider_rates)
                scenario = payload.get("scenario", "normal")
                if scenario not in {
                    "normal",
                    "failure_spike",
                    "mercadopago_spike",
                    "chile_bancoestado_spike",
                }:
                    raise ValueError("Escenario de ingestión inválido")
                self.send_json(
                    200,
                    LIVE_STREAM.update_configuration(provider_rates, rules, scenario),
                )
                return
            if path == "/api/live/start":
                rows_per_minute = validate_rows_per_minute(
                    payload.get("rows_per_minute")
                )
                start_at = validate_live_start(payload.get("start_at"))
                provider_rates = validate_provider_rates(payload.get("provider_rates"))
                rules = validate_decline_rules(payload.get("rules", []), provider_rates)
                self.send_json(
                    202,
                    LIVE_STREAM.start(
                        rows_per_minute,
                        start_at,
                        provider_rates,
                        rules,
                    ),
                )
                return
            requested_rows = validate_row_count(payload.get("rows", N_TRANSACTIONS))
            filename = validate_csv_filename(payload.get("filename", OUTPUT_PATH.name))
            start_date, end_date = validate_generation_dates(
                payload.get("start_date", START_DATE.isoformat()),
                payload.get("end_date", END_DATE.isoformat()),
            )
            csv_path = BASE_DIR / filename
            provider_rates = validate_provider_rates(payload.get("provider_rates"))
            rules = validate_decline_rules(payload.get("rules", []), provider_rates)

            started = time.monotonic()
            rows = generate_csv(
                csv_path,
                n=requested_rows,
                provider_rates=provider_rates,
                decline_rules=rules,
                start_date=start_date,
                end_date=end_date,
            )
            audit_csv(
                csv_path,
                rows,
                start_date=start_date,
                end_date=end_date,
            )
            elapsed = round(time.monotonic() - started, 1)
            self.send_json(
                200,
                {
                    "message": "CSV generado",
                    "rows": rows,
                    "filename": filename,
                    "start_date": start_date.isoformat(sep=" "),
                    "end_date": end_date.isoformat(sep=" "),
                    "seconds": elapsed,
                    "download": f"/download?filename={quote(filename)}",
                },
            )
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})
        except Exception as error:
            self.send_json(500, {"error": f"No se pudo generar el CSV: {error}"})
        finally:
            GENERATION_LOCK.release()

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8002"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Front disponible en http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
