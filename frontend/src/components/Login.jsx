import { useState } from "react";
import MensagemErro from "./MensagemErro";
import { getAgenciaUrl } from "../services/api";
const AGENCIAS = ["http://localhost:4046","http://localhost:4047","http://localhost:4048"];
export default function Login({ onLogin, erroExterno }) {
  const [idConta, setIdConta] = useState("");
  const [senha, setSenha] = useState("");
  const [agencia, setAgencia] = useState(getAgenciaUrl());
  const [erro, setErro] = useState(null);
  const [carregando, setCarregando] = useState(false);
  async function handleSubmit(e) {
    e.preventDefault(); setErro(null); setCarregando(true);
    try { await onLogin(idConta, senha, agencia); }
    catch (err) { setErro(err.message); }
    finally { setCarregando(false); }
  }
  return (
    <div style={{ minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:"#f1f5f9" }}>
      <div style={{ background:"#fff",borderRadius:12,padding:"2rem",width:360,boxShadow:"0 4px 24px #0001" }}>
        <h1 style={{ textAlign:"center",margin:0,color:"#1e40af" }}>ICEIBank</h1>
        <p style={{ textAlign:"center",color:"#64748b",fontSize:13,marginBottom:"1.5rem" }}>Sistema Distribuido de Agencias Bancarias</p>
        <form onSubmit={handleSubmit}>
          <label style={{ display:"block",fontSize:13,fontWeight:600,color:"#374151",marginBottom:4,marginTop:12 }}>Agencia</label>
          <select value={agencia} onChange={e => setAgencia(e.target.value)} style={{ width:"100%",padding:"8px 10px",borderRadius:6,border:"1px solid #d1d5db",fontSize:14,boxSizing:"border-box" }}>
            {AGENCIAS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <label style={{ display:"block",fontSize:13,fontWeight:600,color:"#374151",marginBottom:4,marginTop:12 }}>ID da Conta</label>
          <input type="number" value={idConta} onChange={e => setIdConta(e.target.value)} required style={{ width:"100%",padding:"8px 10px",borderRadius:6,border:"1px solid #d1d5db",fontSize:14,boxSizing:"border-box" }} placeholder="Ex: 0" />
          <label style={{ display:"block",fontSize:13,fontWeight:600,color:"#374151",marginBottom:4,marginTop:12 }}>Senha</label>
          <input type="password" value={senha} onChange={e => setSenha(e.target.value)} required style={{ width:"100%",padding:"8px 10px",borderRadius:6,border:"1px solid #d1d5db",fontSize:14,boxSizing:"border-box" }} placeholder="Senha da conta" />
          <MensagemErro mensagem={erro || erroExterno} onFechar={() => setErro(null)} />
          <button type="submit" disabled={carregando} style={{ width:"100%",padding:"10px",background:"#1d4ed8",color:"#fff",border:"none",borderRadius:6,fontWeight:600,cursor:"pointer",marginTop:16,fontSize:15 }}>
            {carregando ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <p style={{ textAlign:"center",fontSize:12,color:"#888",marginTop:12 }}>Senha padrao: 1234. Use POST /auth/bootstrap para criar acesso.</p>
      </div>
    </div>
  );
}