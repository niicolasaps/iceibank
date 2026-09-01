import { useState } from "react";
import { useAuth } from "./hooks/useAuth";
import Login from "./components/Login";
import ConsultaSaldo from "./components/ConsultaSaldo";
import Deposito from "./components/Deposito";
import Saque from "./components/Saque";
import Transferencia from "./components/Transferencia";
import { api } from "./services/api";

const ABAS = ["Saldo","Depositar","Sacar","Transferir"];

export default function App() {
  const { estaLogado, login, logout, erro: erroAuth, agenciaAtual } = useAuth();
  const [aba, setAba] = useState("Saldo");
  const [status, setStatus] = useState(null);

  async function carregarStatus() {
    try { setStatus(await api.status()); } catch { setStatus(null); }
  }

  if (!estaLogado) return <Login onLogin={login} erroExterno={erroAuth} />;

  return (
    <div style={{ minHeight:"100vh", background:"#f1f5f9", fontFamily:"system-ui,sans-serif" }}>
      <div style={{ background:"#1e40af", color:"#fff", padding:"14px 24px", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <span style={{ fontWeight:700, fontSize:18 }}>ICEIBank</span>
        <span style={{ fontSize:12, opacity:0.8 }}>{agenciaAtual}</span>
        <div style={{ display:"flex", gap:12 }}>
          <button onClick={carregarStatus} style={btnHdr}>Status</button>
          <button onClick={logout} style={btnHdr}>Sair</button>
        </div>
      </div>
      {status && (
        <div style={{ background:"#dbeafe", padding:"8px 24px", fontSize:13, display:"flex", gap:24, justifyContent:"center" }}>
          <span>Agencia: <b>{status.agencia}</b></span>
          <span>Lamport: <b>{status.relogioLamportAtual}</b></span>
          <span>Contas: <b>{status.quantidadeContas}</b></span>
          <button onClick={()=>setStatus(null)} style={{ background:"none", border:"none", cursor:"pointer" }}>x</button>
        </div>
      )}
      <div style={{ display:"flex", background:"#fff", borderBottom:"1px solid #e2e8f0" }}>
        {ABAS.map(a => (
          <button key={a} onClick={()=>setAba(a)}
            style={{ padding:"12px 20px", background:"none", border:"none", cursor:"pointer",
              fontWeight:aba===a?700:400, borderBottom:aba===a?"3px solid #1d4ed8":"3px solid transparent",
              color:aba===a?"#1d4ed8":"#64748b", fontSize:14 }}>
            {a}
          </button>
        ))}
      </div>
      <div style={{ maxWidth:640, margin:"24px auto", padding:"0 16px" }}>
        {aba==="Saldo"      && <ConsultaSaldo />}
        {aba==="Depositar"  && <Deposito />}
        {aba==="Sacar"      && <Saque />}
        {aba==="Transferir" && <Transferencia />}
      </div>
    </div>
  );
}
const btnHdr={ background:"rgba(255,255,255,0.15)", border:"none", color:"#fff", padding:"6px 12px", borderRadius:6, cursor:"pointer", fontSize:13 };