import { useState } from "react";
import { api } from "../services/api";
import MensagemErro from "./MensagemErro";

export default function Saque() {
  const [id, setId] = useState(""); const [valor, setValor] = useState(""); const [res, setRes] = useState(null); const [erro, setErro] = useState(null);

  async function sacar(e) {
    e.preventDefault(); setErro(null); setRes(null);
    try { setRes(await api.sacar(Number(id), Number(valor))); }
    catch (err) { setErro(err.message); }
  }

  return (
    <div style={card}>
      <h3>💸 Sacar</h3>
      <form onSubmit={sacar} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input type="number" value={id} onChange={e => setId(e.target.value)} placeholder="ID da conta" required style={inp} />
        <input type="number" value={valor} onChange={e => setValor(e.target.value)} placeholder="Valor (R$)" step="0.01" required style={inp} />
        <button type="submit" style={btn}>Sacar</button>
      </form>
      <MensagemErro mensagem={erro} onFechar={() => setErro(null)} />
      {res && <div style={ok}>✅ Saque realizado! Novo saldo: <b>R$ {res.saldo.toFixed(2)}</b></div>}
    </div>
  );
}

const card = { background: "#fff", borderRadius: 10, padding: "1.2rem", marginBottom: 16, boxShadow: "0 2px 8px #0001" };
const inp = { padding: "7px 10px", borderRadius: 6, border: "1px solid #d1d5db", flex: 1, fontSize: 14, minWidth: 120 };
const btn = { padding: "7px 16px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 };
const ok = { marginTop: 10, padding: 10, background: "#ecfdf5", borderRadius: 6, color: "#065f46" };
