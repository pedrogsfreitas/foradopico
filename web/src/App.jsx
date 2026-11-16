import { useEffect, useState } from "react";
import Lotacao from "./Lotacao.jsx";
import MinhaSemana from "./MinhaSemana.jsx";

const TABS = [
  { id: "lotacao", label: "Lotação prevista" },
  { id: "minha-semana", label: "Minha semana" },
];

function tabFromHash() {
  const id = window.location.hash.replace("#", "");
  return TABS.some((tab) => tab.id === id) ? id : "lotacao";
}

export default function App() {
  const [tab, setTab] = useState(tabFromHash);

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <>
      <a className="skip" href="#conteudo">
        Pular para o conteúdo
      </a>
      <header className="topo">
        <div className="topo-in">
          <p className="marca">
            Fora<span>Do</span>Pico
          </p>
          <nav aria-label="Telas">
            {TABS.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                aria-current={tab === item.id ? "page" : undefined}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main id="conteudo">{tab === "lotacao" ? <Lotacao /> : <MinhaSemana />}</main>
    </>
  );
}
