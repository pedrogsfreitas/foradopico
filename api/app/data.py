"""Leitura das views da camada Ouro (Databricks) exportadas em CSV.

O Databricks Free Edition não expõe os dados para fora, então a equipe de
Big Data exporta as duas views que o app consome e elas entram na imagem
como arquivos somente leitura. Nenhuma das duas tem nome, e-mail ou
qualquer dado pessoal: o funcionário aparece apenas como um hash.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))

FORECAST_VIEW = "vw_app_lotacao_prevista"
MY_WEEK_VIEW = "vw_app_minha_semana"
SOURCE_LAYER = "Ouro · Databricks"

WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


@dataclass(frozen=True)
class Slot:
    slot: str
    expected_entries: float
    crowding_index: float
    category: str


def _read(view: str) -> list[dict[str, str]]:
    path = DATA_DIR / f"{view}.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class GoldData:
    """Mantém as duas views em memória, indexadas para as consultas do app."""

    def __init__(self) -> None:
        self.forecast: dict[tuple[str, str, str], list[Slot]] = defaultdict(list)
        self.stations: list[dict[str, str]] = []
        self.my_week: dict[str, list[dict[str, str]]] = defaultdict(list)
        self.employees: list[dict[str, str]] = []
        self._load_forecast()
        self._load_my_week()

    def _load_forecast(self) -> None:
        seen: set[tuple[str, str]] = set()
        for row in _read(FORECAST_VIEW):
            key = (row["linha_nome"], row["estacao_nome"], row["dia_semana_nome"])
            self.forecast[key].append(
                Slot(
                    slot=row["faixa"],
                    expected_entries=float(row["entradas_previstas"]),
                    crowding_index=float(row["indice_lotacao"]),
                    category=row["categoria"],
                )
            )
            seen.add((row["linha_nome"], row["estacao_nome"]))
        for slots in self.forecast.values():
            slots.sort(key=lambda item: item.slot)
        self.stations = [
            {"lineName": line, "stationName": station} for line, station in sorted(seen)
        ]

    def _load_my_week(self) -> None:
        teams: dict[str, str] = {}
        for row in _read(MY_WEEK_VIEW):
            self.my_week[row["funcionario_chave"]].append(row)
            teams[row["funcionario_chave"]] = row["time_nome"]
        for rows in self.my_week.values():
            rows.sort(key=lambda item: item["data"])
        self.employees = [
            {"employeeKey": key, "teamName": team}
            for key, team in sorted(teams.items(), key=lambda item: (item[1], item[0]))
        ]

    def slots(self, line: str, station: str, weekday: str) -> list[Slot]:
        return self.forecast.get((line, station, weekday), [])

    def lines_of(self, station: str) -> list[str]:
        return [s["lineName"] for s in self.stations if s["stationName"] == station]

    def category_at(self, station: str, weekday: str, slot: str) -> str | None:
        """Categoria prevista para embarcar numa estação, num dia e faixa.

        Estações de integração (ex.: Sé) existem em mais de uma linha; como a
        view Minha semana não informa a linha, vale a mais lotada.
        """
        found: Slot | None = None
        for line in self.lines_of(station):
            for item in self.slots(line, station, weekday):
                if item.slot == slot and (found is None or item.crowding_index > found.crowding_index):
                    found = item
        return found.category if found else None

    def weeks_of(self, employee_key: str) -> list[str]:
        mondays = {week_start(date.fromisoformat(r["data"])) for r in self.my_week.get(employee_key, [])}
        return [d.isoformat() for d in sorted(mondays)]


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def one_hour_before(hhmm: str) -> str:
    hours, minutes = hhmm.split(":")
    return f"{(int(hours) - 1) % 24:02d}:{minutes}"
