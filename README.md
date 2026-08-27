# ICEIBank — Sprint 1

Projeto acadêmico de Sistemas Distribuídos — **Sprint 1 de 4**: API REST / MVC + Relógio Lógico de Lamport.

## Descrição

O ICEIBank é um banco simplificado dividido em **3 agências** (particionamento, não replicação).
Cada agência é o mesmo código executado 3 vezes, identificada por `AGENCIA_ID` (0, 1 ou 2).

A conta pertence à agência determinada por `agencia_responsavel = id_conta % 3`.

Toda operação é carimbada com um **Relógio de Lamport** e registrada em log `.jsonl`.

## Estrutura

```
iceibank/
├── agencia/
│   ├── requirements.txt
│   └── src/
│       ├── main.py                  # Ponto de entrada FastAPI
│       ├── config.py                # Particionamento e configuração
│       ├── routes.py                # Router FastAPI
│       ├── controllers/
│       │   └── contas_controller.py
│       └── services/
│           ├── lamport_clock.py
│           └── event_log.py
├── evidencias/
│   └── sprint1/
├── RESPOSTAS.md
└── README.md
```

## Pré-requisitos

- Python 3.10+
- pip

## Instalação

```powershell
cd iceibank/agencia
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução das 3 agências (PowerShell — 3 terminais separados)

```powershell
# Terminal 1 — Agência 0 (porta 4000)
$env:AGENCIA_ID="0"; uvicorn src.main:app --port 4000 --reload

# Terminal 2 — Agência 1 (porta 4001)
$env:AGENCIA_ID="1"; uvicorn src.main:app --port 4001 --reload

# Terminal 3 — Agência 2 (porta 4002)
$env:AGENCIA_ID="2"; uvicorn src.main:app --port 4002 --reload
```

## Testes rápidos (PowerShell / Invoke-RestMethod)

```powershell
# Criar conta 0 na Agência 0 (id=0, 0%3=0 ✔)
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas" `
  -ContentType "application/json" `
  -Body '{"id": 0, "nomeAluno": "Maria Silva", "saldoInicial": 500}'

# Consultar saldo
Invoke-RestMethod -Uri "http://localhost:4000/contas/0"

# Depositar
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas/0/depositar" `
  -ContentType "application/json" -Body '{"valor": 200}'

# Sacar
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas/0/sacar" `
  -ContentType "application/json" -Body '{"valor": 100}'

# Saldo insuficiente (deve retornar 400)
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas/0/sacar" `
  -ContentType "application/json" -Body '{"valor": 9999}'

# Conta que NÃO pertence à Agência 0 (id=1, 1%3=1 ≠ 0 → deve retornar 400)
Invoke-RestMethod -Method Post -Uri "http://localhost:4000/contas" `
  -ContentType "application/json" `
  -Body '{"id": 1, "nomeAluno": "João", "saldoInicial": 100}'
```

## Documentação interativa

Cada agência expõe o Swagger UI automático do FastAPI:
- http://localhost:4000/docs
- http://localhost:4001/docs
- http://localhost:4002/docs

## Sprints futuros

| Sprint | Tema |
|--------|------|
| 2 | Mensageria + Relógio Vetorial |
| 3 | App Flutter + Eleição de Líder |
| 4 | Containers + Transações Distribuídas (2PC/Saga) |
