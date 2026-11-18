import { useEffect, useState } from "react";
import { getJson } from "./api.js";
import { Selo } from "./Lotacao.jsx";

const SOURCE = {
  vision: { label: "Câmera (visão computacional)", unit: "pessoas na imagem" },
  device: { label: "Dispositivo ESP32", unit: "pessoas contadas" },
};

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
    const timer = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <section aria-labelledby="t-vivo">
      <h1 id="t-vivo">Ao vivo na plataforma</h1>
      <p className="sub">
        Contagens enviadas pela câmera e pelo dispositivo na estação, ao lado do que a previsão indicava para este horário.
      </p>
      {error && <p className="aviso" role="alert">{error}</p>}

      {data && (
        <>
          <p className="resumo">{data.weekday}, faixa das {data.slot}</p>
          {data.readings.length ? (
            <ul className="cartoes">
              {data.readings.map((reading) => {
                const source = SOURCE[reading.source];
                return (
                  <li key={`${reading.source}-${reading.stationName}`} className="cartao">
                    <p className="titulo">{reading.stationName}</p>
                    <p className="nota">{source.label} · {reading.sourceId}</p>
                    <p className="numero">
                      <strong>{reading.peopleCount.toLocaleString("pt-BR")}</strong> {source.unit}
                    </p>
                    {reading.densityCategory && (
                      <p>Medido agora: <Selo category={reading.densityCategory} /></p>
                    )}
                    <p>
                      Previsão para o horário:{" "}
                      {reading.forecastCategory ? <Selo category={reading.forecastCategory} /> : "sem previsão"}
                    </p>
                    <p className="nota">
                      {reading.minutesAgo === 0 ? "Agora há pouco" : `Há ${reading.minutesAgo} min`}
                      {reading.simulated && " · leitura simulada"}
                    </p>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="vazio-msg">Nenhuma câmera ou dispositivo enviou leituras ainda.</p>
          )}
          <footer className="fonte">
            Fontes: visão computacional e dispositivo físico (leituras) ·{" "}
            <code>{data.forecastSource.view}</code> ({data.forecastSource.layer}) para a previsão
          </footer>
        </>
      )}
    </section>
  );
}
