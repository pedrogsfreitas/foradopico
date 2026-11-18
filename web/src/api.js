// Cliente mínimo da API. Erros viram mensagens em português para a tela.
export async function getJson(path, params = {}, options = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null)
  ).toString();
  let response;
  try {
    response = await fetch(query ? `${path}?${query}` : path, options);
  } catch {
    throw new Error("Sem conexão com o servidor. Verifique sua internet e tente de novo.");
  }
  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json()).detail;
    } catch {
      /* resposta sem corpo JSON */
    }
    const error = new Error(
      typeof detail === "string" && detail ? detail : "Não foi possível carregar os dados agora."
    );
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

export function postJson(path, body, headers = {}) {
  return getJson(path, {}, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

// Categorias do contrato com o robô (inglês) para o rótulo exibido.
export const CONTRACT_CATEGORY = {
  empty: "Vazio",
  moderate: "Moderado",
  full: "Cheio",
  critical: "Crítico",
};

export const LINE_STATUS = {
  normal: { label: "Operação normal", tone: "vazio" },
  degraded: { label: "Velocidade reduzida", tone: "moderado" },
  stopped: { label: "Paralisada", tone: "critico" },
  closed: { label: "Encerrada", tone: "" },
  unknown: { label: "Sem informação", tone: "" },
};

export function formatDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  });
}

export function formatDate(iso) {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

export const CATEGORY_CLASS = {
  Vazio: "vazio",
  Moderado: "moderado",
  Cheio: "cheio",
  "Crítico": "critico",
};
export const CATEGORIES = ["Vazio", "Moderado", "Cheio", "Crítico"];
