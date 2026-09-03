export default function MensagemErro({ mensagem, tipo = "error", onFechar }) {
  if (!mensagem) return null;
  const icons = { error: "✕", success: "✓" };
  return (
    <div className={`alert alert-${tipo}`}>
      <span style={{ fontSize: "1rem" }}>{icons[tipo]}</span>
      <span style={{ flex: 1 }}>{mensagem}</span>
      {onFechar && (
        <button className="alert-close" onClick={onFechar}>✕</button>
      )}
    </div>
  );
}