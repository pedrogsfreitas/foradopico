// Cliente mínimo da API. Erros viram mensagens em português para a tela.
export async function getJson(path, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null)
  ).toString();
  let response;
  try {
    response = await fetch(query ? `${path}?${query}` : path);
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
    throw new Error(
      typeof detail === "string" && detail ? detail : "Não foi possível carregar os dados agora."
    );
  }
  return response.json();
}

export const CATEGORY_CLASS = {
  Vazio: "vazio",
  Moderado: "moderado",
  Cheio: "cheio",
  "Crítico": "critico",
};
export const CATEGORIES = ["Vazio", "Moderado", "Cheio", "Crítico"];
