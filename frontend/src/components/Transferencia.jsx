import { useState } from "react";
import { api } from "../services/api";
import MensagemErro from "./MensagemErro";

export default function Transferencia() {
  const [idOrigem, setIdOrigem] = useState("");
  const [idDestino, setIdDestino] = useState("");
  const [valor, setValor] = useState("");
  const [res, setRes] = useState(null);
  const [erro, setErro] = useState(null);
  const [loading, setLoading] = useState(false);

  async function transferir(e) {
    e.preventDefault(); setErro(null); setRes(null); setLoading(true);
    try { setRes(await api.transferir(Number(idOrigem), Number(idDestino), Number(valor))); }
    catch (err) { setErro(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="card">
      <div className="card-title">🔄 Transferência</div>
      <p className="card-desc">Transfira entre contas da mesma agência ou de agências diferentes.</p>

      <div className="info-box">
        <span>ℹ️</span>
        <span>
          O sistema detecta automaticamente se é local ou entre agências pelo ID.
          Conta 0, 3, 6 → Ag. 0 &nbsp;·&nbsp; Conta 1, 4, 7 → Ag. 1 &nbsp;·&nbsp; Conta 2, 5, 8 → Ag. 2
        </span>
      </div>

      <form onSubmit={transferir}>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Conta Origem</label>
            <input className="form-input" type="number" value={idOrigem} onChange={e => setIdOrigem(e.target.value)} placeholder="Ex: 0" required />
          </div>
          <div className="form-group">
            <label className="form-label">Conta Destino</label>
            <input className="form-input" type="number" value={idDestino} onChange={e => setIdDestino(e.target.value)} placeholder="Ex: 1" required />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Valor (R$)</label>
          <input className="form-input" type="number" value={valor} onChange={e => setValor(e.target.value)} placeholder="0,00" step="0.01" min="0.01" required />
        </div>

        <MensagemErro mensagem={erro} onFechar={() => setErro(null)} />

        {res && (
          <MensagemErro
            mensagem={res.mensagem || "Transferência concluída!"}
            tipo="success"
            onFechar={() => setRes(null)}
          />
        )}

        <button type="submit" disabled={loading} className="btn btn-purple btn-full" style={{ marginTop: "0.5rem" }}>
          {loading ? "⏳ Processando..." : "🔄 Confirmar Transferência"}
        </button>
      </form>
    </div>
  );
}