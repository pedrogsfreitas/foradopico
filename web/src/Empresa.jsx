import { useCallback, useEffect, useState } from "react";
import { CONTRACT_CATEGORY, formatDate, getJson, postJson } from "./api.js";
import { Selo } from "./Lotacao.jsx";

const STATUS = {
  pendingApproval: "Aguardando aprovação",
  approved: "Aprovada",
  rejected: "Recusada",
};

export default function Empresa() {
  // O código fica só na memória desta aba; não é gravado no navegador.
  const [code, setCode] = useState("");
  const [typed, setTyped] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(null);

  const load = useCallback(async (accessCode) => {
    const headers = { headers: { "X-Hr-Code": accessCode } };
    try {
      const [dashboard, schedules, plans] = await Promise.all([
        getJson("/api/hr/dashboard", {}, headers),
        getJson("/api/hr/schedules", {}, headers),
        getJson("/api/hr/contingencyPlans", {}, headers),
      ]);
      setData({ dashboard, schedules, plans });
      setError("");
      return true;
    } catch (e) {
      setError(e.status === 401 ? "Código de acesso incorreto." : e.message);
      return false;
    }
  }, []);

  useEffect(() => {
    if (!code) return undefined;
    const timer = setInterval(() => load(code), 30000);
    return () => clearInterval(timer);
  }, [code, load]);

  async function enter(event) {
    event.preventDefault();
    if (await load(typed)) setCode(typed);
  }

  async function decide(path) {
    try {
      await postJson(path, undefined, { "X-Hr-Code": code });
    } catch (e) {
      setError(e.message);
    }
    load(code);
  }

  if (!code) {
    return (
      <section aria-labelledby="t-empresa">
        <h1 id="t-empresa">Empresa (RH)</h1>
        <p className="sub">Área do RH: aprovar a escala sugerida, decidir o plano B e acompanhar os indicadores.</p>
        <form className="pergunta estreito" onSubmit={enter}>
          <label htmlFor="codigo">Código de acesso do RH</label>
          <input id="codigo" type="password" autoComplete="off" value={typed} onChange={(e) => setTyped(e.target.value)} />
          <div className="acoes">
            <button type="submit" disabled={!typed}>Entrar</button>
          </div>
        </form>
        {error && <p className="aviso" role="alert">{error}</p>}
      </section>
    );
  }

  const { dashboard, schedules, plans } = data;
  const { impact, business, operation } = dashboard;

  return (
    <section aria-labelledby="t-empresa">
      <h1 id="t-empresa">Empresa (RH)</h1>
      <p className="sub">O app sugere, a pessoa decide: nada é publicado para os funcionários sem a sua aprovação.</p>
      {error && <p className="aviso" role="alert">{error}</p>}
      {!dashboard.storagePersistent && (
        <p className="aviso neutro">Ambiente de demonstração: os dados desta área são apagados quando o serviço reinicia.</p>
      )}

      <h2>Indicadores das escalas aprovadas</h2>
      <ul className="indicadores">
        <Indicador value={impact.peakTripsAvoided} label="viagens no pico evitadas" detail={`de ${impact.peakTripsBefore} na escala original`} />
        <Indicador value={`${impact.averageCrowdingReductionPct}%`} label="de lotação a menos, em média" detail="pontos do índice de lotação por viagem" />
        <Indicador value={business.activeEmployees} label="funcionários ativos" detail={`${business.companies} empresa(s)`} />
        <Indicador value={business.approvalRatePct === null ? "—" : `${business.approvalRatePct}%`} label="das sugestões aprovadas" detail={`${business.schedulesPending} aguardando`} />
        <Indicador value={operation.plansApproved} label="planos B acionados" detail={`${operation.alerts} falha(s) detectada(s)`} />
        <Indicador value={operation.noticesDelivered} label="avisos entregues" detail="agendas e planos B, por e-mail" />
      </ul>

      <h2>Escalas</h2>
      {schedules.length === 0 && <p className="vazio-msg">Nenhuma escala importada ainda. O robô envia a planilha do RH para cá.</p>}
      {schedules.map((schedule) => (
        <article key={schedule.scheduleId} className="cartao largo">
          <div className="cabecalho">
            <p className="titulo">{schedule.companyName} · semana {schedule.week}</p>
            <span className={`selo ${schedule.status === "approved" ? "vazio" : schedule.status === "rejected" ? "critico" : "moderado"}`}>
              {STATUS[schedule.status]}
            </span>
          </div>
          <p>
            Escala original: <strong>{schedule.impact.peakTripsBefore}</strong> viagens no pico. Sugerida:{" "}
            <strong>{schedule.impact.peakTripsAfter}</strong>. Ao todo, {schedule.impact.trips} idas ao escritório.
          </p>
          <p className="nota">
            A escala original considera todos entrando na janela das {schedule.assignments[0]?.baselineEntryWindow ?? "08:00"}.
            {schedule.rejectedRows > 0 && ` ${schedule.rejectedRows} linha(s) da planilha foram recusadas na validação.`}
            {schedule.status === "approved" && (schedule.dispatched ? " Agendas enviadas a todos." : " Agendas na fila de envio do robô.")}
          </p>
          <div className="acoes">
            {schedule.status === "pendingApproval" && (
              <>
                <button type="button" onClick={() => decide(`/api/hr/schedules/${schedule.scheduleId}/approve`)}>Aprovar escala</button>
                <button type="button" className="secundario" onClick={() => decide(`/api/hr/schedules/${schedule.scheduleId}/reject`)}>Recusar</button>
              </>
            )}
            <button type="button" className="secundario" aria-expanded={open === schedule.scheduleId} onClick={() => setOpen(open === schedule.scheduleId ? null : schedule.scheduleId)}>
              {open === schedule.scheduleId ? "Ocultar pessoas" : "Ver quem vai em cada dia"}
            </button>
          </div>
          {open === schedule.scheduleId && (
            <div className="rolagem">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Dia</th><th scope="col">Time</th><th scope="col">Pessoa</th><th scope="col">Estação</th>
                    <th scope="col">Entrada</th><th scope="col">Antes</th><th scope="col">Depois</th>
                  </tr>
                </thead>
                <tbody>
                  {schedule.assignments.map((a) => (
                    <tr key={a.assignmentId}>
                      <td>{formatDate(a.date)}</td>
                      <td>{a.teamName}</td>
                      <td>{a.name}</td>
                      <td>{a.boardingStation}</td>
                      <td>{a.remote ? "Remoto (plano B)" : a.entryWindow}</td>
                      <td>{a.baselineCrowding ? <Selo category={CONTRACT_CATEGORY[a.baselineCrowding]} /> : "—"}</td>
                      <td>{a.remote ? "—" : a.predictedCrowding ? <Selo category={CONTRACT_CATEGORY[a.predictedCrowding]} /> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      ))}

      <h2>Plano B</h2>
      {plans.length === 0 && <p className="vazio-msg">Nenhum plano B proposto. Quando uma linha falha, o robô propõe um aqui.</p>}
      {plans.map((plan) => (
        <article key={plan.planId} className="cartao largo">
          <div className="cabecalho">
            <p className="titulo">
              {formatDate(plan.date)} · Time {plan.teamName} · {plan.actionLabel}
              {plan.newEntryWindow && ` para ${plan.newEntryWindow}`}
            </p>
            <span className={`selo ${plan.status === "approved" ? "vazio" : plan.status === "rejected" ? "critico" : "moderado"}`}>
              {STATUS[plan.status]}
            </span>
          </div>
          <p>{plan.reason}</p>
          <p className="nota">
            {plan.affected.length} pessoa(s) afetada(s).
            {plan.status === "approved" && (plan.dispatched ? " Avisos enviados." : " Avisos na fila de envio do robô.")}
          </p>
          {plan.status === "pendingApproval" && (
            <div className="acoes">
              <button type="button" onClick={() => decide(`/api/hr/contingencyPlans/${plan.planId}/approve`)}>Aprovar plano B</button>
              <button type="button" className="secundario" onClick={() => decide(`/api/hr/contingencyPlans/${plan.planId}/reject`)}>Recusar</button>
            </div>
          )}
        </article>
      ))}
      <footer className="fonte">
        Fontes: planilha do RH e monitor de linhas (robô RPA) · <code>vw_app_lotacao_prevista</code> (Ouro · Databricks) para a lotação
      </footer>
    </section>
  );
}

function Indicador({ value, label, detail }) {
  return (
    <li>
      <strong>{value}</strong>
      <span>{label}</span>
      <small>{detail}</small>
    </li>
  );
}
