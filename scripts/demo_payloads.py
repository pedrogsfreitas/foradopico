"""Dados fictícios de demonstração (empresa, times e funcionários inventados)."""
from __future__ import annotations

from datetime import date, timedelta

STATIONS = [
    ("Corinthians-Itaquera", 3), ("Artur Alvim", 3), ("Penha", 3), ("Tatuapé", 3),
    ("Palmeiras-Barra Funda", 3), ("Tucuruvi", 1), ("Santana", 1), ("Jabaquara", 1),
    ("Saúde", 1), ("Ana Rosa", 1),
]


def schedule_import(monday: date) -> dict:
    days = [monday + timedelta(days=i) for i in range(5)]
    iso = monday.isocalendar()
    employees = []
    for index in range(16):
        station, line = STATIONS[index % len(STATIONS)]
        team = "Financeiro" if index < 8 else "Tecnologia"
        employee = {
            "employeeId": f"F{index + 1:04d}",
            "name": f"Pessoa Fictícia {index + 1}",
            "email": f"pessoa{index + 1}@empresa-ficticia.example",
            "teamName": team,
            "boardingStation": station,
            "lineNumber": line,
            "monthlyOnSiteDays": 8 if index % 3 else 12,
        }
        if index % 5 == 0:
            employee["latestEntryWindow"] = "09:30"
        if index % 7 == 0:
            employee["unavailableDates"] = [days[4].isoformat()]
        employees.append(employee)

    def demand(counts, mandatory_day):
        return [
            {"date": d.isoformat(), "minPeople": low, "maxPeople": high, "mandatory": i == mandatory_day}
            for i, (d, (low, high)) in enumerate(zip(days, counts))
        ]

    return {
        "companyName": "Empresa Fictícia S.A.",
        "week": f"{iso.year}-W{iso.week:02d}",
        "entryWindows": ["07:00", "08:00", "09:30", "10:30"],
        "teams": [
            {"teamName": "Financeiro", "demand": demand([(3, 8), (2, 6), (4, 8), (2, 6), (1, 4)], 2)},
            {"teamName": "Tecnologia", "demand": demand([(4, 8), (3, 8), (3, 8), (2, 6), (2, 6)], 0)},
        ],
        "employees": employees,
        "rejectedRows": 1,
    }


def line_status(now_iso: str, line3: str = "stopped") -> dict:
    text = {"normal": "Operação Normal", "stopped": "Paralisada", "degraded": "Velocidade Reduzida"}
    return {
        "collectedAt": now_iso,
        "source": "simulated",
        "stale": False,
        "lines": [
            {"lineNumber": 1, "lineName": "Azul", "status": "normal", "rawText": text["normal"]},
            {"lineNumber": 3, "lineName": "Vermelha", "status": line3, "rawText": text[line3]},
        ],
    }
