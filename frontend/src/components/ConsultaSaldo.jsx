import { useState } from "react";
import { api } from "../services/api";
import MensagemErro from "./MensagemErro";

function fmtBRL(v) {
  return v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ConsultaSaldo() {
  const [id, setId] = useState("");
  const [conta, setConta] = useState(null);
  const [erro, setErro] = useState(null);
  const [loading, setLoading] = useState(false);

  async function consultar(e) {
    e.preventDefault();
    setErro(null); setConta(null); setLoading(true);
    try { setConta(await api.consultarSaldo(Number(id))); }
    catch (err) { setErro(err.message); }
    finally { setLoading(false); }
  }

  const [reais, centavos] = conta ? fmtBRL(conta.saldo).split(",") : ["0", "00"];

  return (
    <div>
      <div className="search-row">
        <input
          className="form-input"
          type="number"
          value={id}
          onChange={e => setId(e.target.value)}
          placeholder="ID da conta (ex: 0)"
        />
        <button
          onClick={consultar}
          disabled={loading || !id}
          className="btn btn-gold"
          style={{ whiteSpace: "nowrap", padding: "0.8rem 1.5rem" }}
        >
          {loading ? "⏳" : "🔍 Consultar"}
        </button>
      </div>

      <MensagemErro mensagem={erro} onFechar={() => setErro(null)} />

      {conta && (
        <div className="balance-hero">
          <div className="balance-label">💰 Saldo Disponível</div>
          <div className="balance-amount">
            <span className="currency">R$&nbsp;</span>
            {reais},{centavos}
          </div>
          <div className="balance-meta">
            <b>{conta.nomeAluno}</b> &nbsp;·&nbsp; Conta <b>#{conta.id}</b>
          </div>

          <div style={{ marginTop: "1.25rem", display: "flex", gap: "1.5rem" }}>
            <div>
              <div style={{ fontSize: "0.68rem", color: "rgba(241,245,249,0.4)", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700 }}>Status</div>
              <div style={{ fontSize: "0.85rem", color: "#10b981", fontWeight: 600, marginTop: 2 }}>● Ativa</div>
            </div>
            <div>
              <div style={{ fontSize: "0.68rem", color: "rgba(241,245,249,0.4)", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700 }}>Titular</div>
              <div style={{ fontSize: "0.85rem", color: "rgba(241,245,249,0.75)", fontWeight: 600, marginTop: 2 }}>{conta.nomeAluno}</div>
            </div>
          </div>
        </div>
      )}

      {!conta && !erro && (
        <div style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px dashed rgba(255,255,255,0.08)",
          borderRadius: 14,
          padding: "3rem 2rem",
          textAlign: "center",
          color: "rgba(241,245,249,0.25)"
        }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem" }}>🏧</div>
          <div style={{ fontSize: "0.9rem" }}>Digite o ID da conta e clique em Consultar</div>
        </div>
      )}
    </div>
  );
}