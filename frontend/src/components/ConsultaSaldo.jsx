import { useState } from "react";
import { api } from "../services/api";
import MensagemErro from "./MensagemErro";
export default function ConsultaSaldo() {
  const [id,setId]=useState(""); const [conta,setConta]=useState(null); const [erro,setErro]=useState(null);
  async function consultar(e) { e.preventDefault(); setErro(null); setConta(null); try { setConta(await api.consultarSaldo(Number(id))); } catch(err){setErro(err.message);} }
  return (<div style={card}><h3>Consultar Saldo</h3><form onSubmit={consultar} style={{display:"flex",gap:8}}><input type="number" value={id} onChange={e=>setId(e.target.value)} placeholder="ID da conta" required style={inp}/><button type="submit" style={btn}>Consultar</button></form><MensagemErro mensagem={erro} onFechar={()=>setErro(null)}/>{conta&&<div style={res}><b>{conta.nomeAluno}</b> (conta {conta.id}) - Saldo: <b>R$ {conta.saldo.toFixed(2)}</b></div>}</div>);
}
const card={background:"#fff",borderRadius:10,padding:"1.2rem",marginBottom:16,boxShadow:"0 2px 8px #0001"};
const inp={padding:"7px 10px",borderRadius:6,border:"1px solid #d1d5db",flex:1,fontSize:14};
const btn={padding:"7px 16px",background:"#1d4ed8",color:"#fff",border:"none",borderRadius:6,cursor:"pointer",fontWeight:600};
const res={marginTop:10,padding:10,background:"#eff6ff",borderRadius:6,fontSize:15};