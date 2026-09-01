/**
 * api.js — Model: chamadas à API do ICEIBank
 * Guarda/recupera o token JWT do localStorage.
 * Injeta automaticamente Authorization: Bearer <token> em todas as requisições.
 */

const AGENCIA_KEY = "iceibank_agencia";
const TOKEN_KEY = "iceibank_token";

export function getAgenciaUrl() {
  return localStorage.getItem(AGENCIA_KEY) || "http://localhost:4046";
}

export function setAgenciaUrl(url) {
  localStorage.setItem(AGENCIA_KEY, url);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${getAgenciaUrl()}${path}`, { ...options, headers });

  if (resp.status === 401) {
    clearToken();
    throw new Error("Não autorizado. Faça login novamente.");
  }

  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "Erro na requisição.");
  return data;
}

export const api = {
  login: (idConta, senha) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ idConta, senha }) }),

  registrarSenha: (idConta, senha) =>
    request("/auth/registrar", { method: "POST", body: JSON.stringify({ idConta, senha }) }),

  criarConta: (id, nomeAluno, saldoInicial, senha) =>
    request("/contas", { method: "POST", body: JSON.stringify({ id, nomeAluno, saldoInicial, senha }) }),

  consultarSaldo: (id) => request(`/contas/${id}`),

  depositar: (id, valor) =>
    request(`/contas/${id}/depositar`, { method: "POST", body: JSON.stringify({ valor }) }),

  sacar: (id, valor) =>
    request(`/contas/${id}/sacar`, { method: "POST", body: JSON.stringify({ valor }) }),

  transferir: (idOrigem, idDestino, valor) =>
    request("/transferencias", { method: "POST", body: JSON.stringify({ idOrigem, idDestino, valor }) }),

  status: () => request("/status"),
};
