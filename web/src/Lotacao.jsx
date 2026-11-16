import { useEffect, useMemo, useState } from "react";
import { CATEGORIES, CATEGORY_CLASS, getJson } from "./api.js";
import Fonte from "./Fonte.jsx";

const DEFAULT = { line: "3-Vermelha", station: "Corinthians-Itaquera", weekday: "Segunda" };

export default function Lotacao() {
  const [catalog, setCatalog] = useState(null);
  const [choice, setChoice] = useState(DEFAULT);
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson("/api/stations").then(setCatalog).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    let active = true;
    setError("");
    getJson("/api/crowdingForecast", choice)
      .then((data) => active && setForecast(data))
      .catch((e) => {
        if (active) {
          setForecast(null);
          setError(e.message);
        }
      });
    return () => {
      active = false;
    };
  }, [choice]);

  const lines = useMemo(
    () => [...new Set((catalog?.stations ?? []).map((s) => s.lineName))],
    [catalog]
  );
  const stationsOfLine = (catalog?.stations ?? []).filter((s) => s.lineName === choice.line);

  function changeLine(line) {
    const first = catalog.stations.find((s) => s.lineName === line);
    setChoice({ ...choice, line, station: first.stationName });
  }

  const peak = forecast ? Math.max(...forecast.slots.map((s) => s.crowdingIndex), 1) : 1;
  const best = new Set((forecast?.highlights ?? []).map((h) => h.best.slot));

  return (
    <section aria-labelledby="t-lotacao">
      <h1 id="t-lotacao">Lotação prevista</h1>
      <p className="sub">Veja como a estação costuma estar a cada 15 minutos e escolha a melhor hora para embarcar.</p>

      <form className="filtros" onSubmit={(e) => e.preventDefault()}>
        <label>
          Linha
          <select value={choice.line} onChange={(e) => changeLine(e.target.value)} disabled={!catalog}>
            {(lines.length ? lines : [choice.line]).map((line) => (
              <option key={line}>{line}</option>
            ))}
          </select>
        </label>
        <label>
          Estação
          <select
            value={choice.station}
            onChange={(e) => setChoice({ ...choice, station: e.target.value })}
            disabled={!catalog}
          >
            {(stationsOfLine.length ? stationsOfLine : [{ stationName: choice.station }]).map((s) => (
              <option key={s.stationName}>{s.stationName}</option>
            ))}
          </select>
        </label>
        <label>
          Dia
          <select value={choice.weekday} onChange={(e) => setChoice({ ...choice, weekday: e.target.value })}>
            {(catalog?.weekdays ?? [choice.weekday]).map((day) => (
              <option key={day}>{day}</option>
            ))}
          </select>
        </label>
      </form>

      {error && (
        <p className="aviso" role="alert">
          {error}
        </p>
      )}

      {forecast && (
        <>
          <div className="destaques">
            {forecast.highlights.map((h) => (
              <article key={h.period} className="destaque">
                <h2>{h.period}</h2>
                <p className="hora">
                  <span className="rot">Melhor horário</span>
                  <strong>{h.best.slot}</strong>
                  <Selo category={h.best.category} />
                </p>
                <p className="hora evite">
                  <span className="rot">Evite</span>
                  <strong>{h.avoid.slot}</strong>
                  <Selo category={h.avoid.category} />
                </p>
              </article>
            ))}
          </div>

          <figure className="grafico">
            <figcaption>
              {forecast.stationName} · Linha {forecast.lineName} · {forecast.weekday}
            </figcaption>
            <div className="rolagem">
              <div className="barras" role="img" aria-label={describe(forecast)}>
                {forecast.slots.map((s) => (
                  <div
                    key={s.slot}
                    className={`barra ${CATEGORY_CLASS[s.category]}${best.has(s.slot) ? " melhor" : ""}`}
                    style={{ height: `${Math.max(4, (s.crowdingIndex / peak) * 100)}%` }}
                    title={`${s.slot} · ${s.category} · ${s.expectedEntries.toLocaleString("pt-BR")} entradas`}
                  >
                    {best.has(s.slot) && <span className="marca-melhor">{s.slot}</span>}
                  </div>
                ))}
              </div>
              <div className="eixo" aria-hidden="true">
                {forecast.slots.map((s) => (
                  <span key={s.slot}>{s.slot.endsWith(":00") && Number(s.slot.slice(0, 2)) % 2 === 0 ? s.slot.slice(0, 2) + "h" : ""}</span>
                ))}
              </div>
            </div>
            <ul className="legenda">
              {CATEGORIES.map((category) => (
                <li key={category}>
                  <Selo category={category} />
                </li>
              ))}
              <li className="leg-melhor">Contorno escuro: melhor horário do período</li>
            </ul>
          </figure>

          <details className="tabela">
            <summary>Ver os horários em tabela</summary>
            <table>
              <thead>
                <tr>
                  <th scope="col">Faixa</th>
                  <th scope="col">Lotação</th>
                  <th scope="col">Entradas previstas</th>
                </tr>
              </thead>
              <tbody>
                {forecast.slots.map((s) => (
                  <tr key={s.slot}>
                    <th scope="row">{s.slot}</th>
                    <td>
                      <Selo category={s.category} />
                    </td>
                    <td>{s.expectedEntries.toLocaleString("pt-BR")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>

          <Fonte source={forecast.source} />
        </>
      )}
    </section>
  );
}

export function Selo({ category }) {
  return <span className={`selo ${CATEGORY_CLASS[category] ?? ""}`}>{category}</span>;
}

function describe(forecast) {
  const parts = forecast.highlights.map(
    (h) =>
      `${h.period}: melhor horário ${h.best.slot}, ${h.best.category}; evite ${h.avoid.slot}, ${h.avoid.category}`
  );
  return `Gráfico de lotação por faixa de 15 minutos. ${parts.join(". ")}. A tabela abaixo traz todos os horários.`;
}
