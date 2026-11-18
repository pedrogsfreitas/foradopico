import { useEffect, useState } from "react";
import { LINE_STATUS, formatDate, formatDateTime, getJson } from "./api.js";

export default function Alertas() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const load = () =>
      getJson("/api/alerts")
        .then((body) => active && (setData(body), setError("")))
        .catch((e) => active && setError(e.message));
    load();
    const timer = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const status = data?.lineStatus;

  return (
    <section aria-labelledby="t-alertas">
      <h1 id="t-alertas">Alertas e plano B</h1>
      <p className="sub">Situação das linhas, falhas detectadas e as mudanças de escala já aprovadas pelo RH.</p>
      {error && <p className="aviso" role="alert">{error}</p>}

      {data && (
        <>
          <h2>Situação das linhas</h2>
          {status ? (
            <>
              <ul className="cartoes">
                {status.lines.map((line) => {
                  const info = LINE_STATUS[line.status] ?? LINE_STATUS.unknown;
                  return (
                    <li key={line.lineNumber} className="cartao">
                      <p className="titulo">Linha {line.lineNumber}-{line.lineName}</p>
                      <p><span className={`selo ${info.tone}`}>{info.label}</span></p>
                      <p className="nota">Texto da operadora: {line.rawText}</p>
                    </li>
                  );
                })}
              </ul>
              <p className="nota">
                Coletado em {formatDateTime(status.collectedAt)}
                {status.source === "simulated" && " · dados simulados para demonstração"}
                {status.stale && " · a fonte está fora do ar; esta é a última situação conhecida"}
              </p>
            </>
          ) : (
            <p className="vazio-msg">O monitor de linhas ainda não enviou nenhuma leitura.</p>
          )}

          <h2>Falhas detectadas</h2>
          {data.alerts.length ? (
            <ul className="lista">
              {data.alerts.map((alert) => (
                <li key={alert.alertId}>
                  <strong>{alert.message}</strong>
                  <span className="nota">Detectado em {formatDateTime(alert.detectedAt)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="vazio-msg">Nenhuma falha registrada.</p>
          )}

          <h2>Plano B aprovado pelo RH</h2>
          {data.approvedPlans.length ? (
            <ul className="lista">
              {data.approvedPlans.map((plan, index) => (
                <li key={index}>
                  <strong>
                    {formatDate(plan.date)} · Time {plan.teamName} · {plan.action}
                    {plan.newEntryWindow && ` para ${plan.newEntryWindow}`}
                  </strong>
                  <span className="nota">{plan.reason}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="vazio-msg">Nenhum plano B em vigor.</p>
          )}
          <footer className="fonte">Fonte: robô de automação (RPA), pela API do ForaDoPico</footer>
        </>
      )}
    </section>
  );
}
