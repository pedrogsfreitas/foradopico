import { useEffect, useState } from "react";
import { getJson, postJson } from "./api.js";

const EXAMPLES = [
  "Quantas pessoas entram na Sé na segunda às 18h?",
  "Qual o pico da estação Corinthians-Itaquera na quarta?",
  "Qual o melhor horário para embarcar no Tucuruvi?",
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
        Pergunte sobre a lotação prevista das Linhas 1-Azul e 3-Vermelha: pico, melhor horário e movimento por faixa de
        15 minutos. A resposta cita a fonte ou avisa quando a informação não está na base.
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
          placeholder="Ex.: Quantas pessoas entram na Sé na segunda às 18h?"
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
          {answer.refused && <p><span className="selo">Fora da cobertura: não consta na base</span></p>}
          <p className="texto">{answer.answer || "O assistente não devolveu uma resposta."}</p>
          {answer.sources.length > 0 && (
            <p className="nota">
              Fonte: trecho {answer.sources.map((id) => <code key={id}>{id}</code>).reduce((a, b) => [a, ", ", b])} da base de
              conhecimento, gerada de <code>vw_app_lotacao_prevista</code> (Ouro · Databricks)
              {answer.confidence != null && ` · confiança ${Math.round(answer.confidence * 100)}%`}
            </p>
          )}
          <p className="nota">Resposta gerada por IA local (llama3.1 com RAG e ferramenta de consulta). Os números são estimativas de lotação.</p>
        </article>
      )}
      <footer className="fonte">Fonte: assistente de lotação (Generative AI) · llama3.1:8b e bge-m3 via Ollama, sobre <code>vw_app_lotacao_prevista</code></footer>
    </section>
  );
}
