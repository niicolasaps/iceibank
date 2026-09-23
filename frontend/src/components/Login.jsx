import { useState } from "react";
import { getAgenciaUrl } from "../services/api";
import MensagemErro from "./MensagemErro";

// URLs das agencias - locais para desenvolvimento, Render para producao
const AGENCIAS = [
  // Producao (Render) - substituir pelos links reais apos o deploy
  ...(import.meta.env.VITE_AGENCIA_0_URL ? [
    { url: import.meta.env.VITE_AGENCIA_0_URL, label: "Agencia 0 (Render)" },
    { url: import.meta.env.VITE_AGENCIA_1_URL, label: "Agencia 1 (Render)" },
    { url: import.meta.env.VITE_AGENCIA_2_URL, label: "Agencia 2 (Render)" },
  ] : []),
  // Local (desenvolvimento)
  { url: "http://localhost:4046", label: "Agencia 0 — :4046 (local)" },
  { url: "http://localhost:4047", label: "Agencia 1 — :4047 (local)" },
  { url: "http://localhost:4048", label: "Agencia 2 — :4048 (local)" },
];

export default function Login({ onLogin, erroExterno }) {
  const [idConta, setIdConta] = useState("");
  const [senha, setSenha] = useState("");
  const [agencia, setAgencia] = useState(AGENCIAS[0].url);
  const [erro, setErro] = useState(null);
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      await onLogin(idConta, senha, agencia);
    } catch (err) {
      setErro(err.message);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="login-bg">
      <div className="login-card">
        <div className="login-logo">
          <span className="login-icon">🏦</span>
          <div className="login-title">ICEIBank</div>
          <div className="login-subtitle">Sistema Bancário Distribuído</div>
          <div className="login-divider" />
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Agência</label>
            <select
              className="form-select"
              value={agencia}
              onChange={e => setAgencia(e.target.value)}
            >
              {AGENCIAS.map(a => (
                <option key={a.url} value={a.url}>{a.label}</option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">ID da Conta</label>
              <input
                className="form-input"
                type="number"
                value={idConta}
                onChange={e => setIdConta(e.target.value)}
                placeholder="Ex: 0"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Senha</label>
              <input
                className="form-input"
                type="password"
                value={senha}
                onChange={e => setSenha(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          <MensagemErro mensagem={erro || erroExterno} onFechar={() => setErro(null)} />

          <button
            type="submit"
            disabled={carregando}
            className="btn btn-gold btn-full"
            style={{ marginTop: "1.25rem" }}
          >
            {carregando ? <>⏳ Autenticando...</> : <>🔐 Acessar Conta</>}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: "0.72rem", color: "rgba(241,245,249,0.25)", marginTop: "1.5rem", lineHeight: 1.6 }}>
          Primeiro acesso? Use <code style={{ color: "rgba(212,175,55,0.7)" }}>POST /auth/bootstrap</code><br />
          para criar credenciais via terminal.
        </p>
      </div>
    </div>
  );
}