"""Endpoints do contrato com o robô RPA (docs/productApiContract.yaml).

Ficam na raiz, exatamente como no contrato. Todos exigem X-Api-Key, menos
GET /lineStatus, que é público.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from . import engine
from .schemas import (
    AlertCreate,
    ContingencyPlanCreate,
    DispatchReport,
    LineStatusSnapshot,
    ScheduleImport,
)
from .security import robot_key
from .state import gold, store

router = APIRouter(tags=["robô RPA"])
Status = Query(..., pattern="^(pendingApproval|approved|rejected)$")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def public_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    keys = ("scheduleId", "version", "week", "status", "assignments")
    return {k: schedule[k] for k in keys}


def schedule_dispatched(schedule: dict[str, Any]) -> bool:
    employees = {a["employeeId"] for a in schedule["assignments"]}
    return employees <= store.delivered_to("schedule", schedule["scheduleId"], schedule["version"])


def plan_dispatched(plan: dict[str, Any]) -> bool:
    employees = {a["employeeId"] for a in plan["affected"]}
    return employees <= store.delivered_to("contingencyPlan", plan["planId"], 1)


@router.post("/scheduleImports", dependencies=[Depends(robot_key)])
def schedule_imports(
    body: ScheduleImport,
    idempotency_key: str = Header(..., min_length=64, max_length=64),
):
    existing = store.get_by_key("import", idempotency_key)
    if existing:
        return JSONResponse(existing, status_code=200)

    schedule_id = _new_id("sch")
    assignments = engine.build_assignments(body, gold, schedule_id)
    schedule = {
        "scheduleId": schedule_id,
        "version": 1,
        "week": body.week,
        "status": "pendingApproval",
        "companyName": body.companyName,
        "rejectedRows": body.rejectedRows,
        "entryWindows": sorted(body.entryWindows),
        "teams": [t.teamName for t in body.teams],
        "assignments": assignments,
    }
    store.put("schedule", schedule_id, schedule)
    result = {
        "importId": _new_id("imp"),
        "scheduleId": schedule_id,
        "status": "pendingApproval",
        "receivedEmployees": len(body.employees),
    }
    store.put("import", result["importId"], result, key=idempotency_key)
    return JSONResponse(result, status_code=201)


@router.get("/schedules", dependencies=[Depends(robot_key)])
def schedules(status: str = Status, dispatched: bool | None = None) -> list[dict[str, Any]]:
    found = [s for s in store.all("schedule") if s["status"] == status]
    if dispatched is not None:
        found = [s for s in found if schedule_dispatched(s) == dispatched]
    return [public_schedule(s) for s in found]


@router.get("/assignments", dependencies=[Depends(robot_key)])
def assignments(date: date, lineNumber: int | None = None) -> list[dict[str, Any]]:
    day = date.isoformat()
    found = []
    for schedule in store.all("schedule"):
        if schedule["status"] != "approved":
            continue
        for item in schedule["assignments"]:
            if item["date"] == day and (lineNumber is None or item["lineNumber"] == lineNumber):
                found.append(item)
    return found


@router.post("/lineStatus", status_code=204, dependencies=[Depends(robot_key)])
def post_line_status(body: LineStatusSnapshot) -> Response:
    store.put("lineStatus", "latest", body.model_dump(mode="json"))
    return Response(status_code=204)


@router.get("/lineStatus")
def get_line_status() -> dict[str, Any]:
    snapshot = store.get("lineStatus", "latest")
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Ainda não há situação das linhas registrada.")
    return snapshot


@router.post("/alerts", dependencies=[Depends(robot_key)])
def create_alert(body: AlertCreate):
    existing = store.get_by_key("alert", body.dedupeKey)
    if existing:
        return JSONResponse(existing, status_code=200)
    alert = {**body.model_dump(mode="json"), "alertId": _new_id("alt")}
    store.put("alert", alert["alertId"], alert, key=body.dedupeKey)
    return JSONResponse(alert, status_code=201)


@router.post("/contingencyPlans", dependencies=[Depends(robot_key)])
def create_plan(body: ContingencyPlanCreate):
    if body.action == "shiftEntryWindow" and not body.newEntryWindow:
        return JSONResponse(
            {"errors": [{"field": "newEntryWindow", "message": "Obrigatório quando action = shiftEntryWindow."}]},
            status_code=422,
        )
    key = f"{body.alertId}|{body.teamName}|{body.action}|{body.newEntryWindow or ''}"
    existing = store.get_by_key("plan", key)
    if existing:
        return JSONResponse(existing, status_code=200)

    wanted = set(body.assignmentIds)
    affected = [
        item
        for schedule in store.all("schedule")
        if schedule["status"] == "approved"
        for item in schedule["assignments"]
        if item["assignmentId"] in wanted
    ]
    plan = {
        **body.model_dump(mode="json"),
        "planId": _new_id("pln"),
        "status": "pendingApproval",
        "affected": affected,
    }
    store.put("plan", plan["planId"], plan, key=key)
    return JSONResponse(plan, status_code=201)


@router.get("/contingencyPlans", dependencies=[Depends(robot_key)])
def plans(status: str = Status, dispatched: bool | None = None) -> list[dict[str, Any]]:
    found = [p for p in store.all("plan") if p["status"] == status]
    if dispatched is not None:
        found = [p for p in found if plan_dispatched(p) == dispatched]
    return found


@router.post("/dispatches", status_code=204, dependencies=[Depends(robot_key)])
def dispatches(body: DispatchReport) -> Response:
    for item in body.items:
        version = item.version if item.kind == "schedule" else 1
        store.add_dispatch(item.kind, item.referenceId, item.employeeId, version, item.delivered)
    return Response(status_code=204)
