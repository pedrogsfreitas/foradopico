"""API do ForaDoPico (MVP).

Reúne os componentes das disciplinas em um só produto:
- Big Data: leituras da camada Ouro (lotação prevista e minha semana).
- RPA: contrato com o robô (app/robot.py).
- Visão e Maker Lab: leituras ao vivo; GenAI: assistente; BI: painel do RH
  (app/product.py).
- DevOps: /health e /metrics.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from . import product, robot
from .data import (
    FORECAST_VIEW,
    MY_WEEK_VIEW,
    SOURCE_LAYER,
    WEEKDAYS,
    one_hour_before,
    week_start,
)
from .state import gold

APP_VERSION = os.getenv("APP_VERSION", "dev")
STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parent.parent / "static"))

# Janelas usadas para apontar o melhor horário e o horário a evitar.
PERIODS = {"Manhã": ("05:30", "10:30"), "Tarde": ("16:00", "20:00")}

app = FastAPI(
    title="ForaDoPico API",
    version=APP_VERSION,
    description="Escala presencial fora do pico do transporte sobre trilhos.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(robot.router)
app.include_router(product.router)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Formato combinado com o robô: {"errors": [{"field", "message"}]}.
    errors = [
        {"field": ".".join(str(part) for part in err["loc"][1:]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse({"errors": errors}, status_code=422)


Instrumentator(
    should_group_status_codes=True,
    should_instrument_requests_inprogress=True,
    inprogress_name="http_requests_inprogress",
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, include_in_schema=False)


def _source(view: str) -> dict[str, str]:
    return {"view": view, "layer": SOURCE_LAYER}


@app.get("/health", tags=["operação"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@app.get("/api/stations", tags=["lotação"])
def stations() -> dict:
    return {"weekdays": WEEKDAYS, "stations": gold.stations}


@app.get("/api/crowdingForecast", tags=["lotação"])
def crowding_forecast(
    line: str = Query(..., examples=["3-Vermelha"]),
    station: str = Query(..., examples=["Corinthians-Itaquera"]),
    weekday: str = Query(..., examples=["Segunda"]),
) -> dict:
    slots = gold.slots(line, station, weekday)
    if not slots:
        raise HTTPException(
            status_code=404,
            detail="Não há previsão para essa combinação de linha, estação e dia.",
        )
    highlights = []
    for name, (start, end) in PERIODS.items():
        window = [s for s in slots if start <= s.slot <= end]
        if not window:
            continue
        best = min(window, key=lambda s: s.crowding_index)
        worst = max(window, key=lambda s: s.crowding_index)
        highlights.append(
            {
                "period": name,
                "from": start,
                "to": end,
                "best": {"slot": best.slot, "category": best.category},
                "avoid": {"slot": worst.slot, "category": worst.category},
            }
        )
    return {
        "lineName": line,
        "stationName": station,
        "weekday": weekday,
        "highlights": highlights,
        "slots": [
            {
                "slot": s.slot,
                "expectedEntries": round(s.expected_entries),
                "crowdingIndex": s.crowding_index,
                "category": s.category,
            }
            for s in slots
        ],
        "source": _source(FORECAST_VIEW),
    }


@app.get("/api/employees", tags=["minha semana"])
def employees() -> dict:
    """Chaves anônimas dos funcionários. Simula o login enquanto não há autenticação."""
    return {"employees": gold.employees, "source": _source(MY_WEEK_VIEW)}


@app.get("/api/myWeek", tags=["minha semana"])
def my_week(
    employee_key: str = Query(..., alias="employeeKey", min_length=8, max_length=64),
    week: date | None = Query(None, description="Qualquer dia da semana desejada (ISO 8601)"),
) -> dict:
    rows = gold.my_week.get(employee_key)
    if not rows:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    weeks = gold.weeks_of(employee_key)
    monday = week_start(week) if week else date.fromisoformat(weeks[-1])
    by_date = {r["data"]: r for r in rows}

    days = []
    for offset in range(5):
        day = monday + timedelta(days=offset)
        row = by_date.get(day.isoformat())
        if row is None:
            days.append({"date": day.isoformat(), "weekday": WEEKDAYS[offset], "onSite": False})
            continue
        original_boarding = one_hour_before(row["janela_original"])
        days.append(
            {
                "date": day.isoformat(),
                "weekday": row["dia_semana_nome"],
                "onSite": True,
                "stationName": row["estacao_nome"],
                "entryWindow": row["entrar_no_escritorio"],
                "boardBy": row["embarcar_ate"],
                "predictedCrowding": row["lotacao_prevista"],
                "originalEntryWindow": row["janela_original"],
                "originalBoardBy": original_boarding,
                # Derivado no app: lotação prevista se a pessoa embarcasse para a janela original.
                "originalPredictedCrowding": gold.category_at(
                    row["estacao_nome"], row["dia_semana_nome"], original_boarding
                ),
            }
        )
    return {
        "employeeKey": employee_key,
        "teamName": rows[0]["time_nome"],
        "weekStart": monday.isoformat(),
        "availableWeeks": weeks,
        "days": days,
        "source": _source(MY_WEEK_VIEW),
    }


# O front (build do Vite) é servido pela mesma imagem, na raiz.
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")
