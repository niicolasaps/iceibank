import { useState } from "react";
import { api } from "../services/api";
import MensagemErro from "./MensagemErro";

export default function Transferencia() {
  const [idOrigem, setIdOrigem] = useState(""); const [idDestino, setIdDestino] = useState("");
  const [valor, setValor] = useState(""); const [res, setRes] = useState(null); const [erro, setErro] = useState(null);

  async function transferir(e) {
    e.preventDefault(); setErro(null); setRes(null);
    try { setRes(await api.transferir(Number(idOrigem), Number(idDestino), Number(valor))); }
    catch (err) { setErro(err.message); }
  }

  return (
    <div style={card}>
      <h3>🔄 Transferência</h3>
      <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 10px" }}>
        O backend decide automaticamente se é local (mesma agência) ou entre agências.
      </p>
      <form onSubmit={transferir} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input type="number" value={idOrigem} onChange={e => setIdOrigem(e.target.value)} placeholder="Conta origem" required style={inp} />
        <input type="number" value={idDestino} onChange={e => setIdDestino(e.target.value)} placeholder="Conta destino" required style={inp} />
        <input type="number" value={valor} onChange={e => setValor(e.target.value)} placeholder="Valor (R$)" step="0.01" required style={inp} />
        <button type="submit" style={btn}>Transferir</button>
      </form>
      <MensagemErro mensagem={erro} onFechar={() => setErro(null)} />
      {res && <div style={ok}>✅ {res.mensagem}</div>}
    </div>
  );
}

const card = { background: "#fff", borderRadius: 10, padding: "1.2rem", marginBottom: 16, boxShadow: "0 2px 8px #0001" };
const inp = { padding: "7px 10px", borderRadius: 6, border: "1px solid #d1d5db", flex: 1, fontSize: 14, minWidth: 120 };
const btn = { padding: "7px 16px", background: "#7c3aed", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 };
const ok = { marginTop: 10, padding: 10, background: "#f5f3ff", borderRadius: 6, color: "#4c1d95" };
