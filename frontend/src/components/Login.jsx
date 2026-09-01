import { useState } from "react";
import MensagemErro from "./MensagemErro";
import { api, getAgenciaUrl } from "../services/api";

const AGENCIAS = ["http://localhost:4046", "http://localhost:4047", "http://localhost:4048"];

export default function Login({ onLogin, erroExterno }) {
  const [idConta, setIdConta] = useState("");
  const [senha, setSenha] = useState("");
  const [agencia, setAgencia] = useState(getAgenciaUrl());
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
    <div style={estilos.container}>
      <div style={estilos.card}>
        <h1 style={estilos.titulo}>🏦 ICEIBank</h1>
        <p style={estilos.subtitulo}>Sistema Distribuído de Agências Bancárias</p>
        <form onSubmit={handleSubmit}>
          <label style={estilos.label}>Agência</label>
          <select value={agencia} onChange={e => setAgencia(e.target.value)} style={estilos.input}>
            {AGENCIAS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>

          <label style={estilos.label}>ID da Conta</label>
          <input type="number" value={idConta} onChange={e => setIdConta(e.target.value)} required style={estilos.input} placeholder="Ex: 0" />

          <label style={estilos.label}>Senha</label>
          <input type="password" value={senha} onChange={e => setSenha(e.target.value)} required style={estilos.input} placeholder="Senha da conta" />

          <MensagemErro mensagem={erro || erroExterno} onFechar={() => setErro(null)} />

          <button type="submit" disabled={carregando} style={estilos.btn}>
            {carregando ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <p style={{ textAlign: "center", fontSize: 12, color: "#888", marginTop: 12 }}>
          Para criar conta, use POST /contas na API. A senha padrão é "1234".
        </p>
      </div>
    </div>
  );
}

const estilos = {
  container: { minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f1f5f9" },
  card: { background: "#fff", borderRadius: 12, padding: "2rem", width: 360, boxShadow: "0 4px 24px #0001" },
  titulo: { textAlign: "center", margin: 0, color: "#1e40af" },
  subtitulo: { textAlign: "center", color: "#64748b", fontSize: 13, marginBottom: "1.5rem" },
  label: { display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 4, marginTop: 12 },
  input: { width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 14, boxSizing: "border-box" },
  btn: { width: "100%", padding: "10px", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, fontWeight: 600, cursor: "pointer", marginTop: 16, fontSize: 15 },
};
