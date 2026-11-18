"""Modelos de entrada. Os nomes seguem o contrato com o robô (camelCase)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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


Category = Literal["Vazio", "Moderado", "Cheio", "Crítico"]


class LiveReading(BaseModel):
    """Leitura da visão computacional (contagem de pessoas) ou do robô-sensor ESP32 (ambiente).

    - vision: peopleCount obrigatório (YOLO11 treinado para cabeças).
    - device: ao menos uma medida de ambiente (luz, temperatura, umidade). O
      robô do Maker Lab não conta pessoas.
    """

    source: Literal["vision", "device"]
    sourceId: str = Field(min_length=1, max_length=60, description="Câmera ou dispositivo")
    stationName: str = Field(min_length=1, max_length=80)
    lineName: str | None = Field(default=None, max_length=40)
    capturedAt: datetime | None = None
    simulated: bool = False
    # Visão computacional
    peopleCount: int | None = Field(default=None, ge=0, le=100000)
    capacity: int | None = Field(default=None, ge=1, le=100000)
    crowdingIndex: float | None = Field(default=None, ge=0, le=100)
    densityCategory: Category | None = None
    # Robô-sensor (Maker Lab)
    lightPct: int | None = Field(default=None, ge=0, le=100)
    lightClass: Literal["adequada", "baixa", "critica"] | None = None
    temperatureC: float | None = Field(default=None, ge=-30, le=80)
    humidityPct: float | None = Field(default=None, ge=0, le=100)
    darkZone: bool | None = None
    darkZoneCount: int | None = Field(default=None, ge=0)
    aiAlert: str | None = Field(default=None, max_length=1200)

    @field_validator("densityCategory", mode="before")
    @classmethod
    def accept_unaccented(cls, value):
        # O script da visão escreve "Critico", sem acento.
        return "Crítico" if isinstance(value, str) and value.lower() in ("critico", "crítico") else value

    @model_validator(mode="after")
    def check_source(self):
        if self.source == "vision" and self.peopleCount is None:
            raise ValueError("peopleCount é obrigatório para source = vision")
        if self.source == "device" and all(
            v is None for v in (self.lightPct, self.lightClass, self.temperatureC, self.humidityPct)
        ):
            raise ValueError("informe ao menos lightPct, lightClass, temperatureC ou humidityPct para source = device")
        return self


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)
