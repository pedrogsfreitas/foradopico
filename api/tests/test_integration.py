"""Fluxo completo do contrato com o robô, do import da planilha ao envio das agendas."""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from demo_payloads import line_status, schedule_import  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
ROBOT = {"X-Api-Key": os.environ["ROBOT_API_KEY"]}
SENSOR = {"X-Api-Key": os.environ["SENSOR_API_KEY"]}
HR = {"X-Hr-Code": os.environ["HR_ACCESS_CODE"]}
MONDAY = date(2026, 11, 16)
KEY = "a" * 64


def test_robot_endpoints_require_key():
    assert client.get("/schedules", params={"status": "approved"}).status_code == 401
    assert client.get("/schedules", params={"status": "approved"}, headers={"X-Api-Key": "errada"}).status_code == 401
    assert client.get("/api/hr/schedules").status_code == 401


def test_full_flow():
    payload = schedule_import(MONDAY)

    # 1. Import idempotente: a mesma chave devolve a importação original.
    first = client.post("/scheduleImports", json=payload, headers={**ROBOT, "Idempotency-Key": KEY})
    assert first.status_code == 201, first.text
    again = client.post("/scheduleImports", json=payload, headers={**ROBOT, "Idempotency-Key": KEY})
    assert again.status_code == 200
    assert again.json() == first.json()
    schedule_id = first.json()["scheduleId"]
    assert first.json()["status"] == "pendingApproval"

    # 2. Antes da aprovação o robô não enxerga a escala.
    assert client.get("/schedules", params={"status": "approved"}, headers=ROBOT).json() == []

    # 3. RH vê a sugestão com o impacto e aprova.
    listed = client.get("/api/hr/schedules", headers=HR).json()
    mine = next(s for s in listed if s["scheduleId"] == schedule_id)
    assert mine["impact"]["peakTripsAvoided"] > 0
    assert mine["impact"]["peakTripsAfter"] < mine["impact"]["peakTripsBefore"]
    approved = client.post(f"/api/hr/schedules/{schedule_id}/approve", headers=HR)
    assert approved.status_code == 200
    assert client.post(f"/api/hr/schedules/{schedule_id}/approve", headers=HR).status_code == 409

    # 4. Robô busca escalas aprovadas ainda não enviadas.
    pending = client.get("/schedules", params={"status": "approved", "dispatched": "false"}, headers=ROBOT).json()
    assert [s["scheduleId"] for s in pending] == [schedule_id]
    assignments = pending[0]["assignments"]
    assert all(a["entryWindow"] in a["allowedEntryWindows"] for a in assignments)
    restricted = [a for a in assignments if a["employeeId"] == "F0001"]
    assert restricted and all(a["entryWindow"] <= "09:30" for a in restricted)
    friday = (MONDAY + timedelta(days=4)).isoformat()
    assert not [a for a in assignments if a["employeeId"] == "F0001" and a["date"] == friday]

    # 5. Situação das linhas, alerta idempotente e plano B.
    assert client.post("/lineStatus", json=line_status("2026-11-16T07:40:00-03:00"), headers=ROBOT).status_code == 204
    assert client.get("/lineStatus").json()["lines"][1]["status"] == "stopped"
    alert_body = {
        "dedupeKey": "line3-stopped-2026-11-16",
        "lineNumber": 3,
        "previousStatus": "normal",
        "status": "stopped",
        "detectedAt": "2026-11-16T07:35:00-03:00",
        "message": "Linha 3-Vermelha paralisada desde 07:35.",
    }
    alert = client.post("/alerts", json=alert_body, headers=ROBOT)
    assert alert.status_code == 201
    assert client.post("/alerts", json=alert_body, headers=ROBOT).status_code == 200
    alert_id = alert.json()["alertId"]

    today = client.get("/assignments", params={"date": MONDAY.isoformat(), "lineNumber": 3}, headers=ROBOT).json()
    assert today and all(a["lineNumber"] == 3 for a in today)
    team = today[0]["teamName"]
    ids = [a["assignmentId"] for a in today if a["teamName"] == team]
    plan_body = {
        "alertId": alert_id,
        "date": MONDAY.isoformat(),
        "teamName": team,
        "action": "remoteWork",
        "assignmentIds": ids,
        "reason": "Linha 3-Vermelha paralisada. Sugestão: trabalho remoto hoje.",
    }
    plan = client.post("/contingencyPlans", json=plan_body, headers=ROBOT)
    assert plan.status_code == 201
    assert plan.json()["status"] == "pendingApproval"
    assert len(plan.json()["affected"]) == len(ids)
    assert client.post("/contingencyPlans", json=plan_body, headers=ROBOT).status_code == 200
    plan_id = plan.json()["planId"]

    bad = client.post("/contingencyPlans", json={**plan_body, "action": "shiftEntryWindow"}, headers=ROBOT)
    assert bad.status_code == 422 and bad.json()["errors"][0]["field"] == "newEntryWindow"

    # 6. RH aprova o plano B; a tela pública de alertas não expõe nomes.
    assert client.post(f"/api/hr/contingencyPlans/{plan_id}/approve", headers=HR).status_code == 200
    public = client.get("/api/alerts").text
    assert "Pessoa Fictícia" not in public and "@empresa-ficticia" not in public
    assert client.get("/contingencyPlans", params={"status": "approved", "dispatched": "false"}, headers=ROBOT).json()

    # 7. Robô reporta os envios; a escala deixa de aparecer como pendente.
    employees = sorted({a["employeeId"] for a in assignments})
    report = {
        "runId": "run-1",
        "items": [
            {"kind": "schedule", "referenceId": schedule_id, "version": 1, "employeeId": e, "delivered": True, "channel": "email"}
            for e in employees
        ],
    }
    assert client.post("/dispatches", json=report, headers=ROBOT).status_code == 204
    assert client.get("/schedules", params={"status": "approved", "dispatched": "false"}, headers=ROBOT).json() == []

    # 8. Painel do RH.
    board = client.get("/api/hr/dashboard", headers=HR).json()
    assert board["business"]["activeEmployees"] == len(employees)
    assert board["operation"]["plansApproved"] == 1
    assert board["operation"]["noticesDelivered"] == len(employees)


def test_validation_error_format():
    response = client.post("/scheduleImports", json={"week": "errada"}, headers={**ROBOT, "Idempotency-Key": KEY})
    assert response.status_code == 422
    assert {"field", "message"} <= set(response.json()["errors"][0])


def test_live_readings():
    reading = {"source": "vision", "sourceId": "camera-1", "stationName": "Sé", "peopleCount": 42, "densityCategory": "Cheio"}
    assert client.post("/api/liveReadings", json=reading).status_code == 401
    assert client.post("/api/liveReadings", json=reading, headers=SENSOR).status_code == 201
    device = {"source": "device", "sourceId": "esp32-1", "stationName": "Sé", "peopleCount": 17}
    assert client.post("/api/liveReadings", json=device, headers=SENSOR).status_code == 201
    body = client.get("/api/live").json()
    assert {r["source"] for r in body["readings"]} == {"vision", "device"}


def test_assistant_degrades_gracefully():
    assert client.get("/api/assistant/status").json() == {"configured": False}
    response = client.post("/api/assistant", json={"question": "Posso levar bicicleta no metrô?"})
    assert response.status_code == 503
