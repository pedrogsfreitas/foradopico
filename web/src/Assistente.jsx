import { useEffect, useState } from "react";
import { getJson, postJson } from "./api.js";

const EXAMPLES = [
  "Posso levar bicicleta no metrô?",
  "Quem tem direito à gratuidade?",
  "O que fazer se eu perder um objeto na estação?",
];

export default function Assistente() {
  const [configured, setConfigured] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson("/api/assistant/status")
      .then((data) => setConfigured(data.configured))
      .catch(() => setConfigured(false));
  }, []);

  async function ask(event) {
    event.preventDefault();
    if (question.trim().length < 3) return;
    setLoading(true);
    setError("");
    setAnswer(null);
    try {
      setAnswer(await postJson("/api/assistant", { question: question.trim() }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="t-assistente">
      <h1 id="t-assistente">Pergunte ao ForaDoPico</h1>
      <p className="sub">
        Tire dúvidas sobre regras e direitos do passageiro do Metrô e da CPTM. A resposta cita a fonte ou avisa quando a
        informação não consta.
      </p>

      {configured === false && (
        <p className="aviso neutro">
          O assistente ainda não está conectado neste ambiente. As outras telas continuam funcionando normalmente.
        </p>
      )}

      <form className="pergunta" onSubmit={ask}>
        <label htmlFor="pergunta">Sua pergunta</label>
        <textarea
          id="pergunta"
          rows={3}
          maxLength={500}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ex.: Posso levar bicicleta no metrô?"
        />
        <div className="acoes">
          <button type="submit" disabled={loading || question.trim().length < 3}>
            {loading ? "Consultando…" : "Perguntar"}
          </button>
          {EXAMPLES.map((example) => (
            <button type="button" className="secundario" key={example} onClick={() => setQuestion(example)}>
              {example}
            </button>
          ))}
        </div>
      </form>

      {error && <p className="aviso" role="alert">{error}</p>}

      {answer && (
        <article className="cartao resposta" aria-live="polite">
          {answer.refused && <p><span className="selo">Não consta na base</span></p>}
          <p className="texto">{answer.answer || "O assistente não devolveu uma resposta."}</p>
          {answer.sources.length > 0 && (
            <>
              <h2>Fontes</h2>
              <ul className="lista simples">
                {answer.sources.map((source, index) => (
                  <li key={index}>
                    {source.url ? <a href={source.url} rel="noreferrer noopener" target="_blank">{source.title}</a> : source.title}
                  </li>
                ))}
              </ul>
            </>
          )}
          <p className="nota">Resposta gerada por IA a partir de documentos oficiais. Confira a fonte antes de decidir.</p>
        </article>
      )}
      <footer className="fonte">Fonte: LLM local com base de conhecimento (componente de IA generativa)</footer>
    </section>
  );
}
