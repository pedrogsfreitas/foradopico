import { useEffect, useState } from "react";
import { getJson } from "./api.js";
import { Selo } from "./Lotacao.jsx";

const LIGHT = {
  adequada: { label: "Adequada", tone: "vazio" },
  baixa: { label: "Baixa", tone: "moderado" },
  critica: { label: "Crítica", tone: "critico" },
};

function quando(reading) {
  const m = reading.minutesAgo;
  const texto = m === 0 ? "Agora há pouco" : m < 60 ? `Há ${m} min` : `Há ${Math.floor(m / 60)} h`;
  return `${texto}${m > 5 ? " · sem leituras recentes" : ""}${reading.simulated ? " · leitura simulada" : ""}`;
}

function Historico({ history, capacity }) {
  if (!history || history.length < 2) return null;
  const top = Math.max(capacity || 0, ...history.map((h) => h.people), 1);
  return (
    <div className="mini" role="img" aria-label={`Últimas ${history.length} contagens, de ${history[0].people} a ${history[history.length - 1].people} pessoas`}>
      {history.map((h, i) => (
        <span key={i} style={{ height: `${Math.max(6, (h.people / top) * 100)}%` }} title={`${h.at} · ${h.people} pessoas`} />
      ))}
    </div>
  );
}

function CartaoCamera({ reading }) {
  return (
    <li className="cartao">
      <p className="titulo">{reading.stationName}</p>
      <p className="nota">Câmera da plataforma · {reading.sourceId}</p>
      <p className="numero">
        <strong>{reading.peopleCount.toLocaleString("pt-BR")}</strong> pessoas
        {reading.capacity && <span className="nota"> de {reading.capacity} que a área comporta</span>}
      </p>
      {reading.densityCategory && (
        <p>
          Medido agora: <Selo category={reading.densityCategory} />
          {reading.crowdingIndex != null && <span className="nota"> ({Math.round(reading.crowdingIndex * 100)}%)</span>}
        </p>
      )}
      <p>
        Previsão para o horário:{" "}
        {reading.forecastCategory ? <Selo category={reading.forecastCategory} /> : <span className="nota">sem previsão para esta estação</span>}
      </p>
      <Historico history={reading.history} capacity={reading.capacity} />
      <p className="nota">{quando(reading)}</p>
    </li>
  );
}

function CartaoRobo({ reading }) {
  const light = LIGHT[reading.lightClass];
  return (
    <li className="cartao">
      <p className="titulo">{reading.stationName}</p>
      <p className="nota">Robô-sensor de estação · {reading.sourceId}</p>
      {light && (
        <p>
          Iluminação: <span className={`selo ${light.tone}`}>{light.label}</span>
          {reading.lightPct != null && <span className="nota"> ({reading.lightPct}% de luz)</span>}
        </p>
      )}
      <p className="numero">
        {reading.temperatureC != null && <><strong>{reading.temperatureC.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}</strong> °C </>}
        {reading.humidityPct != null && <span className="nota">· umidade {Math.round(reading.humidityPct)}%</span>}
      </p>
      {reading.darkZone && <p className="aviso">Trecho escuro detectado: o robô parou no local.</p>}
      {reading.darkZoneCount != null && <p className="nota">Trechos escuros nesta ronda: {reading.darkZoneCount}</p>}
      {reading.aiAlert && (
        <blockquote className="ia">
          <p>{reading.aiAlert}</p>
          <footer>Alerta gerado por IA (Gemini) a partir das medições</footer>
        </blockquote>
      )}
      <p className="nota">{quando(reading)}</p>
    </li>
  );
}

export default function AoVivo() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const load = () =>
      getJson("/api/live")
        .then((body) => active && (setData(body), setError("")))
        .catch((e) => active && setError(e.message));
    load();
    const timer = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const cameras = data?.readings.filter((r) => r.source === "vision") ?? [];
  const robots = data?.readings.filter((r) => r.source === "device") ?? [];

  return (
    <section aria-labelledby="t-vivo">
      <h1 id="t-vivo">Ao vivo na plataforma</h1>
      <p className="sub">
        A previsão estima a lotação; a câmera mede. O robô-sensor confere iluminação e conforto térmico da plataforma.
      </p>
      {error && <p className="aviso" role="alert">{error}</p>}

      {data && (
        <>
          <p className="resumo">{data.weekday}, faixa das {data.slot}</p>

          <h2>Lotação medida pela câmera</h2>
          {cameras.length ? (
            <ul className="cartoes">{cameras.map((r) => <CartaoCamera key={r.sourceId} reading={r} />)}</ul>
          ) : (
            <p className="vazio-msg">Nenhuma câmera enviou contagens ainda.</p>
          )}

          <h2>Condições da plataforma (robô-sensor)</h2>
          {robots.length ? (
            <ul className="cartoes">{robots.map((r) => <CartaoRobo key={r.sourceId} reading={r} />)}</ul>
          ) : (
            <p className="vazio-msg">Nenhum robô-sensor enviou leituras ainda.</p>
          )}

          <footer className="fonte">
            Fontes: YOLO11 treinado para contar cabeças (visão computacional), robô ESP32 com LDR e DHT11 (Maker Lab) ·{" "}
            <code>{data.forecastSource.view}</code> ({data.forecastSource.layer}) para a previsão. Nenhuma imagem é enviada:
            só números.
          </footer>
        </>
      )}
    </section>
  );
}
