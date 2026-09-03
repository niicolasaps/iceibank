import { useState } from "react";
import { api } from "../services/api";
import MensagemErro from "./MensagemErro";

export default function Deposito() {
  const [id, setId] = useState("");
  const [valor, setValor] = useState("");
  const [res, setRes] = useState(null);
  const [erro, setErro] = useState(null);
  const [loading, setLoading] = useState(false);

  async function depositar(e) {
    e.preventDefault(); setErro(null); setRes(null); setLoading(true);
    try { setRes(await api.depositar(Number(id), Number(valor))); }
    catch (err) { setErro(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="card">
      <div className="card-title">💰 Depositar</div>
      <p className="card-desc">Adicione saldo a uma conta. O valor será creditado imediatamente.</p>

      <form onSubmit={depositar}>
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
            mensagem={`Depósito realizado! Novo saldo: R$ ${res.saldo.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
            tipo="success"
            onFechar={() => setRes(null)}
          />
        )}

        <button type="submit" disabled={loading} className="btn btn-green btn-full" style={{ marginTop: "0.5rem" }}>
          {loading ? "⏳ Processando..." : "💰 Confirmar Depósito"}
        </button>
      </form>
    </div>
  );
}