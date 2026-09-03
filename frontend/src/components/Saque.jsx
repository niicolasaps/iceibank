import { useState } from "react";
import { api } from "../services/api";
import MensagemErro from "./MensagemErro";

export default function Saque() {
  const [id, setId] = useState("");
  const [valor, setValor] = useState("");
  const [res, setRes] = useState(null);
  const [erro, setErro] = useState(null);
  const [loading, setLoading] = useState(false);

  async function sacar(e) {
    e.preventDefault(); setErro(null); setRes(null); setLoading(true);
    try { setRes(await api.sacar(Number(id), Number(valor))); }
    catch (err) { setErro(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="card">
      <div className="card-title">💸 Sacar</div>
      <p className="card-desc">Retire saldo de uma conta. Certifique-se que há saldo suficiente.</p>

      <form onSubmit={sacar}>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">ID da Conta</label>
            <input className="form-input" type="number" value={id} onChange={e => setId(e.target.value)} placeholder="Ex: 0" required />
          </div>
          <div className="form-group">
            <label className="form-label">Valor (R$)</label>
            <input className="form-input" type="number" value={valor} onChange={e => setValor(e.target.value)} placeholder="0,00" step="0.01" min="0.01" required />
          </div>
        </div>

        <MensagemErro mensagem={erro} onFechar={() => setErro(null)} />

        {res && (
          <MensagemErro
            mensagem={`Saque realizado! Saldo restante: R$ ${res.saldo.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
            tipo="success"
            onFechar={() => setRes(null)}
          />
        )}

        <button type="submit" disabled={loading} className="btn btn-red btn-full" style={{ marginTop: "0.5rem" }}>
          {loading ? "⏳ Processando..." : "💸 Confirmar Saque"}
        </button>
      </form>
    </div>
  );
}