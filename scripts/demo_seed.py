"""Popula a API com dados FICTÍCIOS de demonstração, pelo mesmo contrato que o robô usa.

Serve para demonstrar o MVP quando o robô, a câmera ou o ESP32 não estão ligados.
Tudo o que ele envia é marcado como simulado.

Uso (PowerShell):
    $env:ROBOT_API_KEY="..."; $env:SENSOR_API_KEY="..."
    python scripts/demo_seed.py --url http://localhost:8000

Rode uma vez, aprove a escala na tela "Empresa (RH)" e rode de novo: na
segunda vez ele propõe o plano B para a linha paralisada.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

from demo_payloads import line_status, schedule_import

SAO_PAULO = timezone(timedelta(hours=-3))


def call(base: str, method: str, path: str, key: str | None = None, body=None, extra=None):
    headers = {"Content-Type": "application/json", **(extra or {})}
    if key:
        headers["X-Api-Key"] = key
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 (URL informada pelo operador)
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        print("A URL precisa começar com http:// ou https://")
        return 1
    robot, sensor = os.getenv("ROBOT_API_KEY"), os.getenv("SENSOR_API_KEY")
    if not robot or not sensor:
        print("Defina ROBOT_API_KEY e SENSOR_API_KEY no ambiente (os mesmos valores do .env da API).")
        return 1

    now = datetime.now(SAO_PAULO)
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    day = today if today.weekday() < 5 else monday

    payload = schedule_import(monday)
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    status, result = call(base, "POST", "/scheduleImports", robot, payload, {"Idempotency-Key": key})
    print(f"Planilha do RH: {status} {result}")
    if status not in (200, 201):
        return 1

    status, _ = call(base, "POST", "/lineStatus", robot, line_status(now.isoformat(timespec="seconds")))
    print(f"Situação das linhas (simulada, Linha 3 paralisada): {status}")

    alert = {
        "dedupeKey": f"line3-stopped-{day.isoformat()}",
        "lineNumber": 3,
        "previousStatus": "normal",
        "status": "stopped",
        "detectedAt": now.isoformat(timespec="seconds"),
        "message": f"[SIMULADO] Linha 3-Vermelha paralisada desde {now:%H:%M}.",
    }
    status, created = call(base, "POST", "/alerts", robot, alert)
    print(f"Alerta: {status}")

    for source, source_id, station, count, category in [
        ("vision", "camera-demo-01", "Corinthians-Itaquera", 148, "Crítico"),
        ("device", "esp32-demo-01", "Corinthians-Itaquera", 131, None),
        ("vision", "camera-demo-02", "Tucuruvi", 37, "Moderado"),
    ]:
        reading = {
            "source": source, "sourceId": source_id, "stationName": station,
            "peopleCount": count, "densityCategory": category, "simulated": True,
        }
        status, _ = call(base, "POST", "/api/liveReadings", sensor, reading)
        print(f"Leitura {source} em {station}: {status}")

    status, todays = call(base, "GET", f"/assignments?date={day.isoformat()}&lineNumber=3", robot)
    if status == 200 and todays and isinstance(created, dict):
        teams = sorted({a["teamName"] for a in todays})
        for team in teams:
            plan = {
                "alertId": created["alertId"],
                "date": day.isoformat(),
                "teamName": team,
                "action": "remoteWork",
                "assignmentIds": [a["assignmentId"] for a in todays if a["teamName"] == team],
                "reason": "[SIMULADO] Linha 3-Vermelha paralisada. Sugestão: trabalho remoto hoje.",
            }
            status, _ = call(base, "POST", "/contingencyPlans", robot, plan)
            print(f"Plano B para {team}: {status}")
    else:
        print('Plano B: ainda não há escala aprovada. Aprove em "Empresa (RH)" e rode de novo.')
    return 0


if __name__ == "__main__":
    sys.exit(main())
