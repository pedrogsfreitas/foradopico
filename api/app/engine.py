"""Motor de escala (heurística do MVP).

Regras, na ordem:
1. Dias obrigatórios do time recebem todos os disponíveis (até maxPeople).
2. Nos demais dias entra o mínimo pedido, priorizando quem tem menos dias
   presenciais na semana (rodízio justo).
3. Quem ainda deve dias presenciais (cota semanal = dias no mês ÷ 4) é
   encaixado nos dias com vaga.
4. Em cada dia, quem embarca na estação mais lotada escolhe primeiro a
   janela de entrada com menor lotação prevista. Cada janela aceita no
   máximo metade do grupo, para a equipe não chegar toda no mesmo horário.

A lotação prevista vem da camada Ouro (vw_app_lotacao_prevista).
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from typing import Any

from .data import WEEKDAYS, GoldData, one_hour_before
from .schemas import Employee, ScheduleImport

CATEGORY_TO_CONTRACT = {"Vazio": "empty", "Moderado": "moderate", "Cheio": "full", "Crítico": "critical"}
PEAK = {"Cheio", "Crítico"}
LINE_NAMES = {1: "1-Azul", 3: "3-Vermelha"}


def _forecast(gold: GoldData, employee: Employee, day: date, window: str):
    line = LINE_NAMES.get(employee.lineNumber)
    if line is None:
        return None
    return gold.slot_at(line, employee.boardingStation, WEEKDAYS[day.weekday()], one_hour_before(window))


def _index(slot) -> float:
    # Sem previsão para a estação: valor neutro, para não favorecer nem punir.
    return slot.crowding_index if slot else 0.5


def build_assignments(imp: ScheduleImport, gold: GoldData, schedule_id: str) -> list[dict[str, Any]]:
    windows = sorted(imp.entryWindows)
    baseline_window = "08:00" if "08:00" in windows else windows[0]
    assignments: list[dict[str, Any]] = []

    for team in imp.teams:
        members = [e for e in imp.employees if e.teamName == team.teamName]
        if not members:
            continue
        quota = {e.employeeId: math.ceil(e.monthlyOnSiteDays / 4) for e in members}
        days_of: dict[str, int] = defaultdict(int)
        chosen: dict[date, list[Employee]] = {}

        def available(employee: Employee, day: date) -> bool:
            return day not in employee.unavailableDates

        ordered = sorted(team.demand, key=lambda d: (not d.mandatory, d.date))
        for demand in ordered:
            pool = [e for e in members if available(e, demand.date)]
            if demand.mandatory:
                picked = pool[: demand.maxPeople]
            else:
                pool = [e for e in pool if days_of[e.employeeId] < quota[e.employeeId]]
                pool.sort(key=lambda e: (days_of[e.employeeId], e.employeeId))
                picked = pool[: demand.minPeople]
            for employee in picked:
                days_of[employee.employeeId] += 1
            chosen[demand.date] = picked

        # Regra 3: completar a cota de quem ainda deve dias presenciais.
        for employee in members:
            for demand in sorted(team.demand, key=lambda d: d.date):
                if days_of[employee.employeeId] >= quota[employee.employeeId]:
                    break
                group = chosen[demand.date]
                if employee in group or len(group) >= demand.maxPeople or not available(employee, demand.date):
                    continue
                group.append(employee)
                days_of[employee.employeeId] += 1

        # Regra 4: janelas de entrada.
        for day, group in sorted(chosen.items()):
            cap = max(1, math.ceil(len(group) / 2))
            used: dict[str, int] = defaultdict(int)
            by_worst_commute = sorted(
                group,
                key=lambda e: _index(_forecast(gold, e, day, baseline_window)),
                reverse=True,
            )
            for employee in by_worst_commute:
                allowed = [w for w in windows if not employee.latestEntryWindow or w <= employee.latestEntryWindow]
                allowed = allowed or [windows[0]]
                ranked = sorted(allowed, key=lambda w: (_index(_forecast(gold, employee, day, w)), w))
                window = next((w for w in ranked if used[w] < cap), ranked[0])
                used[window] += 1

                slot = _forecast(gold, employee, day, window)
                base = _forecast(gold, employee, day, baseline_window)
                assignments.append(
                    {
                        "assignmentId": f"{schedule_id}-{len(assignments) + 1:03d}",
                        "employeeId": employee.employeeId,
                        "name": employee.name,
                        "email": employee.email,
                        "teamName": employee.teamName,
                        "lineNumber": employee.lineNumber,
                        "boardingStation": employee.boardingStation,
                        "date": day.isoformat(),
                        "entryWindow": window,
                        "allowedEntryWindows": allowed,
                        "suggestedDepartureTime": one_hour_before(window),
                        "predictedCrowding": CATEGORY_TO_CONTRACT.get(slot.category) if slot else None,
                        # Campos extras, usados pelo painel do RH (antes x depois).
                        "crowdingIndex": slot.crowding_index if slot else None,
                        "baselineEntryWindow": baseline_window,
                        "baselineCrowding": CATEGORY_TO_CONTRACT.get(base.category) if base else None,
                        "baselineCrowdingIndex": base.crowding_index if base else None,
                        "remote": False,
                    }
                )
    return assignments


def impact(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Indicadores de impacto: escala original (todos na janela base) x escala sugerida."""
    peak_contract = {CATEGORY_TO_CONTRACT[c] for c in PEAK}
    on_site = [a for a in assignments if not a.get("remote")]
    known = [a for a in on_site if a.get("crowdingIndex") is not None and a.get("baselineCrowdingIndex") is not None]
    before = sum(1 for a in assignments if a.get("baselineCrowding") in peak_contract)
    after = sum(1 for a in on_site if a.get("predictedCrowding") in peak_contract)
    reduction = (
        sum(a["baselineCrowdingIndex"] - a["crowdingIndex"] for a in known) / len(known) if known else 0.0
    )
    return {
        "trips": len(assignments),
        "peakTripsBefore": before,
        "peakTripsAfter": after,
        "peakTripsAvoided": max(0, before - after),
        "averageCrowdingReductionPct": round(reduction * 100, 1),
    }
