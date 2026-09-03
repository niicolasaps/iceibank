import { useState, useEffect } from "react";
import { useAuth } from "./hooks/useAuth";
import Login from "./components/Login";
import ConsultaSaldo from "./components/ConsultaSaldo";
import Deposito from "./components/Deposito";
import Saque from "./components/Saque";
import Transferencia from "./components/Transferencia";
import { api, getAgenciaUrl } from "./services/api";

const NAV = [
  { id: "saldo",       icon: "💳", label: "Consultar Saldo",   section: "Contas" },
  { id: "depositar",   icon: "💰", label: "Depositar",          section: "Operações" },
  { id: "sacar",       icon: "💸", label: "Sacar",              section: null },
  { id: "transferir",  icon: "🔄", label: "Transferência",      section: null },
  { id: "status",      icon: "📡", label: "Status / Lamport",   section: "Sistema" },
];

function parseJwt(token) {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch { return {}; }
}

export default function App() {
  const { estaLogado, token, login, logout, erro: erroAuth, agenciaAtual } = useAuth();
  const [aba, setAba] = useState("saldo");
  const [statusData, setStatusData] = useState(null);
  const [statusLoading, setStatusLoading] = useState(false);

  const payload = token ? parseJwt(token) : {};
  const agenciaNum = agenciaAtual?.replace(/.*:(\d+)$/, "$1");

  async function carregarStatus() {
    setStatusLoading(true);
    try { setStatusData(await api.status()); }
    catch { setStatusData(null); }
    finally { setStatusLoading(false); }
  }

  useEffect(() => {
    if (aba === "status") carregarStatus();
  }, [aba]);

  if (!estaLogado) return <Login onLogin={login} erroExterno={erroAuth} />;

  const agenciaLabel = agenciaAtual?.replace("http://", "");

  return (
    <div className="dashboard">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div style={{ fontSize: "1.5rem", marginBottom: "0.25rem" }}>🏦</div>
          <div className="brand-name">ICEIBank</div>
          <div className="brand-tagline">Sistema Distribuído</div>
          <div className="agency-pill">
            <span className="agency-dot" />
            {agenciaLabel}
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV.map((item, i) => {
            const prevSection = i > 0 ? NAV[i - 1].section : null;
            const showSection = item.section && item.section !== prevSection;
            return (
              <div key={item.id}>
                {showSection && <div className="nav-section-label">{item.section}</div>}
                <button
                  className={`nav-btn ${aba === item.id ? "active" : ""}`}
                  onClick={() => setAba(item.id)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                </button>
              </div>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {payload.sub && (
            <div style={{ fontSize: "0.75rem", color: "rgba(241,245,249,0.35)", padding: "0 0.5rem 0.75rem", lineHeight: 1.5 }}>
              Conta <span style={{ color: "rgba(241,245,249,0.6)", fontWeight: 600 }}>#{payload.sub}</span>
            </div>
          )}
          <button className="btn btn-danger" onClick={logout}>
            🚪 Sair da Conta
          </button>
        </div>
      </aside>

      {/* MAIN */}
      <main className="main">
        {/* TOPBAR */}
        <div className="topbar">
          <div className="topbar-left">
            <h2>{NAV.find(n => n.id === aba)?.icon} {NAV.find(n => n.id === aba)?.label}</h2>
            <p>ICEIBank — Banco Digital com Relógio de Lamport</p>
          </div>
          <div className="topbar-right">
            <button
              className="status-chip"
              onClick={() => { setAba("status"); }}
              title="Ver status da agência"
            >
              <span className="status-pulse" />
              Agência {agenciaNum} online
            </button>
          </div>
        </div>

        {/* CONTENT */}
        <div className="main-body">
          {aba === "saldo"      && <ConsultaSaldo />}
          {aba === "depositar"  && <Deposito />}
          {aba === "sacar"      && <Saque />}
          {aba === "transferir" && <Transferencia />}

          {aba === "status" && (
            <div>
              {statusLoading && (
                <div style={{ color: "rgba(241,245,249,0.4)", fontSize: "0.9rem" }}>
                  ⏳ Carregando status...
                </div>
              )}
              {statusData && (
                <div>
                  <div className="status-panel">
                    <div className="stat-item">
                      <div className="stat-label">Agência</div>
                      <div className="stat-value">#{statusData.agencia}</div>
                      <div className="stat-sub">Identificador</div>
                    </div>
                    <div className="stat-item">
                      <div className="stat-label">Lamport</div>
                      <div className="stat-value">{statusData.relogioLamportAtual}</div>
                      <div className="stat-sub">Relógio lógico atual</div>
                    </div>
                    <div className="stat-item">
                      <div className="stat-label">Contas</div>
                      <div className="stat-value">{statusData.quantidadeContas}</div>
                      <div className="stat-sub">Sob esta agência</div>
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-title">📡 Sobre o Relógio de Lamport</div>
                    <div className="card-desc" style={{ marginBottom: 0 }}>
                      <p style={{ lineHeight: 1.7, marginBottom: "0.75rem" }}>
                        O relógio lógico avança a cada evento local (depósito, saque, transferência)
                        e se sincroniza com mensagens de outras agências usando a regra{" "}
                        <code style={{ background: "rgba(255,255,255,0.06)", padding: "1px 6px", borderRadius: 4, color: "#d4af37" }}>
                          max(local, recebido) + 1
                        </code>.
                      </p>
                      <p style={{ lineHeight: 1.7, color: "rgba(241,245,249,0.35)" }}>
                        Isso garante que eventos causalmente relacionados sempre tenham timestamps em ordem crescente,
                        permitindo ordenar eventos distribuídos sem um relógio global.
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {!statusLoading && !statusData && (
                <div style={{ color: "rgba(241,245,249,0.4)", fontSize: "0.9rem" }}>
                  Não foi possível carregar o status. Verifique se as agências estão rodando.
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}