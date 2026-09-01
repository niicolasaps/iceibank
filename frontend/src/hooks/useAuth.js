import { useState, useEffect } from "react";
import { getToken, setToken, clearToken, getAgenciaUrl, setAgenciaUrl, api } from "../services/api";

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
    } catch (e) { setErro(e.message); }
  }

  function logout() { clearToken(); setTokenState(null); }

  useEffect(() => {
    const handler = () => setTokenState(getToken());
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  return { estaLogado, token, login, logout, erro, agenciaAtual: getAgenciaUrl() };
}