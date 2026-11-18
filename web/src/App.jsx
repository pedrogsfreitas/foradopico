import { useEffect, useState } from "react";
import Lotacao from "./Lotacao.jsx";
import MinhaSemana from "./MinhaSemana.jsx";
import Alertas from "./Alertas.jsx";
import AoVivo from "./AoVivo.jsx";
import Assistente from "./Assistente.jsx";
import Empresa from "./Empresa.jsx";

const TABS = [
  { id: "lotacao", label: "Lotação prevista", view: Lotacao },
  { id: "minha-semana", label: "Minha semana", view: MinhaSemana },
  { id: "alertas", label: "Alertas", view: Alertas },
  { id: "ao-vivo", label: "Ao vivo", view: AoVivo },
  { id: "assistente", label: "Pergunte", view: Assistente },
  { id: "empresa", label: "Empresa (RH)", view: Empresa },
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

  const View = TABS.find((item) => item.id === tab).view;

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
      <main id="conteudo">
        <View />
      </main>
    </>
  );
}
