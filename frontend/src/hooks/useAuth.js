/**
 * useAuth.js — Controller: logica de login/logout/token
 * Gerencia o estado de autenticacao e expoe funcoes para Login.jsx e App.jsx.
 */

import { useState, useEffect } from "react";
import { api, getToken, setToken, clearToken, getAgenciaUrl, setAgenciaUrl } from "../services/api";

export function useAuth() {
  const [token, setTokenState] = useState(getToken());
  const [erro, setErro] = useState(null);

  const estaLogado = !!token;

  async function login(idConta, senha, agenciaUrl) {
    setErro(null);
    try {
      if (agenciaUrl) setAgenciaUrl(agenciaUrl);
      const data = await api.login(Number(idConta), senha);
      setToken(data.token);
      setTokenState(data.token);
    } catch (e) {
      setErro(e.message);
    }
  }

  function logout() {
    clearToken();
    setTokenState(null);
  }

  // Se o token expirar, a proxima requisicao vai gerar erro 401 no api.js,
  // que limpa o token — o estado estaLogado vira false e a tela de login aparece.
  // Para detectar isso, escutamos o storage:
  useEffect(() => {
    const handler = () => setTokenState(getToken());
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  return { estaLogado, token, login, logout, erro, agenciaAtual: getAgenciaUrl() };
}
