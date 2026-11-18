"""Endpoints usados pelas telas do app (prefixo /api).

- Alertas e situação das linhas: públicos, sem dados pessoais.
- Ao vivo: leituras da visão computacional e do dispositivo ESP32.
- Assistente: repassa a pergunta para a API da LLM local da equipe.
- RH: aprovação de escalas e planos B e painel de indicadores (X-Hr-Code).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from . import engine
from .data import FORECAST_VIEW, SOURCE_LAYER, WEEKDAYS, one_hour_before
from .robot import plan_dispatched, schedule_dispatched
from .schemas import LiveReading, Question
from .security import hr_code, sensor_key
from .state import gold, store

router = APIRouter(prefix="/api")

# São Paulo não tem horário de verão desde 2019: UTC-3 fixo.
SAO_PAULO = timezone(timedelta(hours=-3))
LINE_LABEL = {1: "1-Azul", 3: "3-Vermelha"}
ACTION_LABEL = {"remoteWork": "Trabalho remoto no dia", "shiftEntryWindow": "Mudança da janela de entrada"}


def _now() -> datetime:
    return datetime.now(SAO_PAULO)


# ------------------------------------------------------------ alertas
@router.get("/alerts", tags=["alertas"])
def alerts() -> dict[str, Any]:
    plans = [
        {
            "date": p["date"],
            "teamName": p["teamName"],
            "action": ACTION_LABEL[p["action"]],
            "newEntryWindow": p.get("newEntryWindow"),
            "reason": p["reason"],
        }
        for p in store.all("plan")
        if p["status"] == "approved"
    ]
    return {
        "lineStatus": store.get("lineStatus", "latest"),
        "alerts": store.all("alert")[:20],
        "approvedPlans": plans[:20],
    }


# ------------------------------------------------------------ ao vivo
@router.post("/liveReadings", status_code=201, tags=["ao vivo"], dependencies=[Depends(sensor_key)])
def post_reading(body: LiveReading) -> dict[str, str]:
    captured = (body.capturedAt or _now()).astimezone(SAO_PAULO)
    doc = body.model_dump(mode="json")
    doc["capturedAt"] = captured.isoformat(timespec="seconds")
    store.add_reading(body.source, body.stationName, doc, doc["capturedAt"])
    return {"status": "stored"}


@router.get("/live", tags=["ao vivo"])
def live() -> dict[str, Any]:
    now = _now()
    slot = f"{now.hour:02d}:{now.minute - now.minute % 15:02d}"
    weekday = WEEKDAYS[now.weekday()]
    readings = []
    for reading in store.latest_readings():
        lines = [reading["lineName"]] if reading.get("lineName") else gold.lines_of(reading["stationName"])
        forecast = next(
            (s for line in lines if (s := gold.slot_at(line, reading["stationName"], weekday, slot))), None
        )
        age = now - datetime.fromisoformat(reading["capturedAt"])
        readings.append(
            {
                **reading,
                "minutesAgo": max(0, int(age.total_seconds() // 60)),
                "forecastCategory": forecast.category if forecast else None,
            }
        )
    return {
        "now": now.isoformat(timespec="seconds"),
        "slot": slot,
        "weekday": weekday,
        "readings": readings,
        "forecastSource": {"view": FORECAST_VIEW, "layer": SOURCE_LAYER},
    }


# ---------------------------------------------------------- assistente
@router.get("/assistant/status", tags=["assistente"])
def assistant_status() -> dict[str, bool]:
    return {"configured": bool(os.getenv("LLM_API_URL"))}


@router.post("/assistant", tags=["assistente"])
def assistant(body: Question) -> dict[str, Any]:
    url = os.getenv("LLM_API_URL")
    if not url:
        raise HTTPException(status_code=503, detail="O assistente ainda não está conectado neste ambiente.")
    try:
        response = httpx.post(url, json={"question": body.question}, timeout=45)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="O assistente está fora do ar agora. Tente de novo em alguns minutos.",
        ) from None

    sources = []
    for item in data.get("sources") or []:
        if isinstance(item, str):
            sources.append({"title": item[:200], "url": None})
        elif isinstance(item, dict):
            link = item.get("url")
            sources.append(
                {
                    "title": str(item.get("title") or item.get("source") or "Fonte")[:200],
                    "url": link if isinstance(link, str) and link.startswith("https://") else None,
                }
            )
    return {
        "answer": str(data.get("answer") or "")[:4000],
        "refused": bool(data.get("refused")),
        "sources": sources[:8],
    }


# ------------------------------------------------------------------ RH
hr = APIRouter(prefix="/hr", tags=["RH"], dependencies=[Depends(hr_code)])


def _hr_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    return {
        **schedule,
        "dispatched": schedule_dispatched(schedule) if schedule["status"] == "approved" else False,
        "impact": engine.impact(schedule["assignments"]),
    }


@hr.get("/schedules")
def hr_schedules() -> list[dict[str, Any]]:
    return [_hr_schedule(s) for s in store.all("schedule")]


def _decide(kind: str, doc_id: str, id_field: str, decision: str) -> dict[str, Any]:
    doc = store.get(kind, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")
    if doc["status"] != "pendingApproval":
        raise HTTPException(status_code=409, detail="Este registro já foi decidido.")
    doc["status"] = decision
    doc["decidedAt"] = _now().isoformat(timespec="seconds")
    store.put(kind, doc[id_field], doc)
    return doc


@hr.post("/schedules/{schedule_id}/{decision}")
def decide_schedule(schedule_id: str, decision: str) -> dict[str, Any]:
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=404, detail="Ação desconhecida.")
    status = "approved" if decision == "approve" else "rejected"
    return _hr_schedule(_decide("schedule", schedule_id, "scheduleId", status))


@hr.get("/contingencyPlans")
def hr_plans() -> list[dict[str, Any]]:
    return [
        {**p, "actionLabel": ACTION_LABEL[p["action"]], "dispatched": plan_dispatched(p) if p["status"] == "approved" else False}
        for p in store.all("plan")
    ]


@hr.post("/contingencyPlans/{plan_id}/{decision}")
def decide_plan(plan_id: str, decision: str) -> dict[str, Any]:
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=404, detail="Ação desconhecida.")
    plan = _decide("plan", plan_id, "planId", "approved" if decision == "approve" else "rejected")
    if plan["status"] == "approved":
        _apply_plan(plan)
    return plan


def _apply_plan(plan: dict[str, Any]) -> None:
    """Plano B aprovado altera as escalas cobertas: remoto ou nova janela."""
    wanted = set(plan["assignmentIds"])
    for schedule in store.all("schedule"):
        changed = False
        for item in schedule["assignments"]:
            if item["assignmentId"] not in wanted:
                continue
            changed = True
            if plan["action"] == "remoteWork":
                item["remote"] = True
            else:
                item["entryWindow"] = plan["newEntryWindow"]
                item["suggestedDepartureTime"] = one_hour_before(plan["newEntryWindow"])
        if changed:
            store.put("schedule", schedule["scheduleId"], schedule)


@hr.get("/dashboard")
def dashboard() -> dict[str, Any]:
    schedules = store.all("schedule")
    approved = [s for s in schedules if s["status"] == "approved"]
    rejected = [s for s in schedules if s["status"] == "rejected"]
    all_assignments = [a for s in approved for a in s["assignments"]]
    plans = store.all("plan")
    decided = len(approved) + len(rejected)
    return {
        "impact": engine.impact(all_assignments),
        "business": {
            "companies": len({s["companyName"] for s in approved}),
            "activeEmployees": len({a["employeeId"] for a in all_assignments}),
            "schedulesApproved": len(approved),
            "schedulesPending": sum(1 for s in schedules if s["status"] == "pendingApproval"),
            "approvalRatePct": round(100 * len(approved) / decided) if decided else None,
        },
        "operation": {
            "alerts": len(store.all("alert")),
            "plansApproved": sum(1 for p in plans if p["status"] == "approved"),
            "plansPending": sum(1 for p in plans if p["status"] == "pendingApproval"),
            "noticesDelivered": store.count_dispatches(),
        },
        "storagePersistent": store.persistent,
    }


router.include_router(hr)
