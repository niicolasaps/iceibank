# ICEIBank

Projeto acadêmico de **Sistemas Distribuídos** — banco simplificado com 3 agências particionadas,
implementando Relógio Lógico de Lamport e API REST/MVC com FastAPI.

## Estrutura do Projeto

```
iceibank/
├── agencia/           # Serviço de agência (mesmo código, 3 instâncias)
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── config.py
│       ├── routes.py
│       ├── controllers/
│       └── services/
├── frontend/          # Sprint futuro (Parte G)
├── evidencias/
│   └── sprint1/
├── RESPOSTAS.md
└── README.md
```

## Particionamento

- Número de agências: **3**
- Conta pertence à agência: `id_conta % 3`
- Portas: Agência 0 → 4000, Agência 1 → 4001, Agência 2 → 4002

## Como executar

### Pré-requisitos

```powershell
cd agencia
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Subir as 3 agências (3 terminais separados)

```powershell
# Terminal 1 — Agência 0
$env:AGENCIA_ID="0"; uvicorn src.main:app --port 4000 --reload

# Terminal 2 — Agência 1
$env:AGENCIA_ID="1"; uvicorn src.main:app --port 4001 --reload

# Terminal 3 — Agência 2
$env:AGENCIA_ID="2"; uvicorn src.main:app --port 4002 --reload
```

### Testar com PowerShell

```powershell
# Criar conta 0 (pertence à agência 0)
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas" `
  -ContentType "application/json" `
  -Body '{"id": 0, "nomeAluno": "Alice", "saldoInicial": 1000}'

# Consultar saldo
Invoke-RestMethod -Uri "http://localhost:4000/contas/0"

# Depositar
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas/0/depositar" `
  -ContentType "application/json" -Body '{"valor": 500}'

# Sacar
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas/0/sacar" `
  -ContentType "application/json" -Body '{"valor": 200}'
```

## Sprints

| Sprint | Tema | Status |
|--------|------|--------|
| 1 | API REST + Relógio de Lamport | ✅ Em andamento |
| 2 | Mensageria + Relógio Vetorial | 🔜 |
| 3 | App Flutter + Eleição de Líder | 🔜 |
| 4 | Containers + 2PC/Saga | 🔜 |
