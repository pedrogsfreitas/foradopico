import { useEffect, useState } from "react";
import { getJson } from "./api.js";
import Fonte from "./Fonte.jsx";
import { Selo } from "./Lotacao.jsx";

function formatDay(iso) {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

export default function MinhaSemana() {
  const [employees, setEmployees] = useState([]);
  const [employeeKey, setEmployeeKey] = useState("");
  const [weekStart, setWeekStart] = useState(null);
  const [week, setWeek] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson("/api/employees")
      .then((data) => {
        setEmployees(data.employees);
        // 66942dc2f3c1d527 tem dias presenciais nas duas semanas da amostra.
        const preferred = data.employees.find((e) => e.employeeKey === "66942dc2f3c1d527");
        setEmployeeKey((preferred ?? data.employees[0]).employeeKey);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!employeeKey) return;
    let active = true;
    setError("");
    getJson("/api/myWeek", { employeeKey, week: weekStart })
      .then((data) => active && setWeek(data))
      .catch((e) => {
        if (active) {
          setWeek(null);
          setError(e.message);
        }
      });
    return () => {
      active = false;
    };
  }, [employeeKey, weekStart]);

  const onSite = week ? week.days.filter((d) => d.onSite).length : 0;

  return (
    <section aria-labelledby="t-semana">
      <h1 id="t-semana">Minha semana</h1>
      <p className="sub">Seus dias presenciais, a janela de entrada sugerida e até que horas embarcar.</p>

      <form className="filtros" onSubmit={(e) => e.preventDefault()}>
        <label>
          Funcionário (login simulado)
          <select
            value={employeeKey}
            onChange={(e) => {
              setWeekStart(null);
              setEmployeeKey(e.target.value);
            }}
          >
            {employees.map((e) => (
              <option key={e.employeeKey} value={e.employeeKey}>
                {e.teamName} · {e.employeeKey.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Semana
          <select value={week?.weekStart ?? ""} onChange={(e) => setWeekStart(e.target.value)} disabled={!week}>
            {(week?.availableWeeks ?? []).map((monday) => (
              <option key={monday} value={monday}>
                Semana de {formatDay(monday)}
              </option>
            ))}
          </select>
        </label>
      </form>

      {error && (
        <p className="aviso" role="alert">
          {error}
        </p>
      )}

      {week && (
        <>
          <p className="resumo">
            Time {week.teamName} · {onSite} {onSite === 1 ? "dia presencial" : "dias presenciais"} nesta semana
          </p>
          <ol className="agenda">
            {week.days.map((day) => (
              <li key={day.date} className={day.onSite ? "dia" : "dia remoto"}>
                <p className="quando">
                  <strong>{day.weekday}</strong> <span>{formatDay(day.date)}</span>
                </p>
                {day.onSite ? (
                  <>
                    <p className="entrada">
                      Entre às <strong>{day.entryWindow}</strong>
                    </p>
                    <p className="embarque">
                      Embarque em {day.stationName} até <strong>{day.boardBy}</strong>
                    </p>
                    <p className="metro">
                      Metrô: <Selo category={day.predictedCrowding} />
                    </p>
                    <p className="antes">
                      Antes: entrada às {day.originalEntryWindow}, embarque até {day.originalBoardBy}
                      {day.originalPredictedCrowding && (
                        <>
                          {" "}
                          <Selo category={day.originalPredictedCrowding} />
                        </>
                      )}
                    </p>
                  </>
                ) : (
                  <p className="entrada">Sem presencial</p>
                )}
              </li>
            ))}
          </ol>
          <Fonte source={week.source} />
        </>
      )}
    </section>
  );
}
