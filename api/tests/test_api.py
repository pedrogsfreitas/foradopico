from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_stations_cover_both_lines():
    body = client.get("/api/stations").json()
    lines = {s["lineName"] for s in body["stations"]}
    assert lines == {"1-Azul", "3-Vermelha"}
    assert len(body["weekdays"]) == 7


def test_forecast_itaquera_monday_peak_is_critical():
    response = client.get(
        "/api/crowdingForecast",
        params={"line": "3-Vermelha", "station": "Corinthians-Itaquera", "weekday": "Segunda"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["slots"]) == 77
    assert body["source"]["view"] == "vw_app_lotacao_prevista"
    morning = next(h for h in body["highlights"] if h["period"] == "Manhã")
    assert morning["avoid"]["category"] == "Crítico"
    assert morning["best"]["category"] == "Vazio"


def test_forecast_unknown_station_is_404():
    response = client.get(
        "/api/crowdingForecast",
        params={"line": "3-Vermelha", "station": "Não existe", "weekday": "Segunda"},
    )
    assert response.status_code == 404


def test_my_week_has_five_days_and_no_personal_data():
    key = client.get("/api/employees").json()["employees"][0]["employeeKey"]
    body = client.get("/api/myWeek", params={"employeeKey": key}).json()
    assert len(body["days"]) == 5
    assert any(day["onSite"] for day in body["days"])
    assert "name" not in body and "email" not in body


def test_my_week_unknown_employee_is_404():
    assert client.get("/api/myWeek", params={"employeeKey": "0000000000000000"}).status_code == 404


def test_metrics_exposed():
    client.get("/health")
    assert "http_requests_total" in client.get("/metrics").text
