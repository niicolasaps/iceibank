export default function MensagemErro({ mensagem, onFechar }) {
  if (!mensagem) return null;
  return (
    <div style={{ background: "#fee2e2", border: "1px solid #ef4444", borderRadius: 6, padding: "10px 14px", margin: "10px 0", color: "#b91c1c", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span>{mensagem}</span>
      {onFechar && <button onClick={onFechar} style={{ background: "none", border: "none", cursor: "pointer", fontWeight: "bold", color: "#b91c1c" }}>x</button>}
    </div>
  );
}