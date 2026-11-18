"""Modelos de entrada. Os nomes seguem o contrato com o robô (camelCase)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

HHMM = r"^\d{2}:\d{2}$"
LineStatusCode = Literal["normal", "degraded", "stopped", "closed", "unknown"]


class Demand(BaseModel):
    date: date
    minPeople: int = Field(ge=0)
    maxPeople: int = Field(ge=0)
    mandatory: bool


class Team(BaseModel):
    teamName: str = Field(min_length=1, max_length=80)
    demand: list[Demand]


class Employee(BaseModel):
    employeeId: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200, pattern=r"^[^@\s]+@[^@\s]+$")
    teamName: str
    boardingStation: str
    lineNumber: int
    monthlyOnSiteDays: int = Field(ge=0, le=23)
    unavailableDates: list[date] = []
    latestEntryWindow: str | None = Field(default=None, pattern=HHMM)


class ScheduleImport(BaseModel):
    companyName: str = Field(min_length=1, max_length=120)
    week: str = Field(pattern=r"^\d{4}-W\d{2}$")
    entryWindows: list[str] = Field(min_length=1)
    teams: list[Team] = Field(min_length=1)
    employees: list[Employee] = Field(min_length=1)
    rejectedRows: int = Field(default=0, ge=0)


class LineStatus(BaseModel):
    lineNumber: int
    lineName: str
    status: LineStatusCode
    rawText: str
    sourceUpdatedAt: datetime | None = None


class LineStatusSnapshot(BaseModel):
    collectedAt: datetime
    source: Literal["metroWebsite", "simulated"]
    stale: bool
    lines: list[LineStatus]


class AlertCreate(BaseModel):
    dedupeKey: str = Field(min_length=1, max_length=120)
    lineNumber: int
    previousStatus: LineStatusCode
    status: LineStatusCode
    detectedAt: datetime
    message: str = Field(min_length=1, max_length=300)


class ContingencyPlanCreate(BaseModel):
    alertId: str
    date: date
    teamName: str
    action: Literal["remoteWork", "shiftEntryWindow"]
    newEntryWindow: str | None = Field(default=None, pattern=HHMM)
    assignmentIds: list[str]
    reason: str = Field(min_length=1, max_length=300)


class DispatchItem(BaseModel):
    kind: Literal["schedule", "contingencyPlan"]
    referenceId: str
    version: int = 1
    employeeId: str
    delivered: bool
    channel: Literal["email"] | None = None
    errorMessage: str | None = None


class DispatchReport(BaseModel):
    runId: str
    items: list[DispatchItem]


class LiveReading(BaseModel):
    """Leitura enviada pela visão computacional (YOLO) ou pelo dispositivo ESP32."""

    source: Literal["vision", "device"]
    sourceId: str = Field(min_length=1, max_length=60, description="Câmera ou dispositivo")
    stationName: str = Field(min_length=1, max_length=80)
    lineName: str | None = Field(default=None, max_length=40)
    peopleCount: int = Field(ge=0, le=100000)
    densityCategory: Literal["Vazio", "Moderado", "Cheio", "Crítico"] | None = None
    capturedAt: datetime | None = None
    simulated: bool = False


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)
