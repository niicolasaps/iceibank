# ICEIBank - Guia de Execucao Completo (Sprint 2)

---

## PARTE 1 - Rodar na sua maquina (ja configurada)

### 1.1 - Subir o backend (3 agencias) - COM RabbitMQ

Abra 3 terminais separados. Em CADA UM, defina RABBITMQ_URL antes de subir:

```powershell
# Terminal 1 - Agencia 0
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload
```

```powershell
# Terminal 2 - Agencia 1
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload
```

```powershell
# Terminal 3 - Agencia 2
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload
```

Quando as 3 subirem corretamente, voce vera em cada terminal:
  [Agencia X] ouvindo na porta 404X
  [Mensageria] Agencia X ouvindo fila: fila-agencia-X

> IMPORTANTE: $env:RABBITMQ_URL precisa ser definida ANTES de subir cada agencia.
> Se voce abrir um terminal novo, defina ela de novo antes de rodar o uvicorn.

### 1.2 - Subir o frontend (interface web)

```powershell
# Terminal 4
cd C:\Users\Nicolas\Desktop\iceibank\frontend
npm run dev
# Abre em http://localhost:5173
```

---

## PARTE 2 - Regra de particionamento de contas

A agencia responsavel por uma conta e: id % 3

- id 0, 3, 6 ... -> Agencia 0 (porta 4046)
- id 1, 4, 7 ... -> Agencia 1 (porta 4047)
- id 2, 5, 8 ... -> Agencia 2 (porta 4048)

---

## PARTE 3 - Criar contas e usar via terminal

### 3.1 - Bootstrap (criar acesso) e Login

```powershell
# Criar acesso para conta 0 na agencia 0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":0,"senha":"minha123"}'

# Fazer login e guardar o token
$tk0 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/login" -ContentType "application/json" -Body '{"idConta":0,"senha":"minha123"}').token
```

### 3.2 - Depositar, sacar e consultar

```powershell
# Depositar R$ 500 na conta 0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas/0/depositar" -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} -Body '{"valor":500}'

# Sacar R$ 50
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas/0/sacar" -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} -Body '{"valor":50}'

# Consultar saldo
Invoke-RestMethod -Uri "http://localhost:4046/contas/0" -Headers @{Authorization="Bearer $tk0"}
```

### 3.3 - Transferencia entre agencias (assincrona via RabbitMQ)

```powershell
# Conta 0 (ag0) -> Conta 1 (ag1) - agora vai pela fila RabbitMQ
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} -Body '{"idOrigem":0,"idDestino":1,"valor":100}'

# Resposta: "Transferencia publicada para a agencia de destino (entrega assincrona)."
# Aguardar 1-2 segundos e verificar que conta 1 recebeu:
$tk1 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4047/auth/login" -ContentType "application/json" -Body '{"idConta":1,"senha":"minha123"}').token
Invoke-RestMethod -Uri "http://localhost:4047/contas/1" -Headers @{Authorization="Bearer $tk1"}
```

### 3.4 - Ver o relogio vetorial

```powershell
# Status mostra o vetor atual de cada agencia
Invoke-RestMethod -Uri "http://localhost:4046/status"
Invoke-RestMethod -Uri "http://localhost:4047/status"
Invoke-RestMethod -Uri "http://localhost:4048/status"
```

### 3.5 - Teste de resiliencia (agencia fora do ar)

```powershell
# 1. Com agencia 1 fora do ar (Ctrl+C no Terminal 2), tente transferir:
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} -Body '{"idOrigem":0,"idDestino":1,"valor":50}'
# Resposta: HTTP 200 - "Transferencia publicada..." (mensagem fica na fila!)

# 2. Suba a agencia 1 novamente - ela vai consumir a mensagem da fila automaticamente
```

### 3.6 - Testar alerta de saldo baixo (funcionalidade adicional)

```powershell
# Fazer saque que deixe o saldo abaixo de R$ 50
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas/0/sacar" -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} -Body '{"valor":460}'
# No terminal da agencia 0 vai aparecer:
# [Alerta] Saldo baixo na conta 0: R$ 40.00 (limite: R$ 50.00)
# [Mensageria] Publicado em agencia.0.alerta-saldo-baixo: {...}
```

### 3.7 - Logs unificados

```powershell
cd C:\Users\Nicolas\Desktop\iceibank\agencia
python mesclar_logs.py
```

---

## PARTE 4 - Usar pelo frontend (http://localhost:5173)

1. Selecione a agencia correta para a conta que quer acessar
2. Digite o ID da conta e a senha
3. Clique em Entrar
4. Use as abas: Saldo / Depositar / Sacar / Transferir / Status

Conta 0 -> agencia http://localhost:4046
Conta 1 -> agencia http://localhost:4047
Conta 2 -> agencia http://localhost:4048

---

## PARTE 5 - Instalar e rodar do ZERO em maquina nova (ex: laboratorio)

### 5.1 - Instalar Git

1. Acesse: https://git-scm.com/download/win
2. Instale com opcoes padrao
3. Verifique: `git --version`

### 5.2 - Instalar Python 3.11

> IMPORTANTE: instale a versao 3.11 ou 3.12. NAO instale Python 3.13 ou 3.14.
> Versoes mais novas causam erro de compilacao do pydantic-core.

1. Acesse: https://www.python.org/downloads/release/python-3119/
2. Baixe "Windows installer (64-bit)"
3. CRITICO: marque "Add Python to PATH" antes de instalar
4. Verifique: `python --version`

### 5.3 - Instalar Node.js

1. Acesse: https://nodejs.org/ -> versao LTS
2. Instale com opcoes padrao
3. Verifique: `node --version`

### 5.4 - Habilitar scripts no PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Responda: S
```

### 5.5 - Clonar o repositorio

```powershell
cd C:\Users\SeuUsuario\Desktop
git clone https://github.com/niicolasps/iceibank.git
cd iceibank
```

### 5.6 - Configurar o ambiente Python

```powershell
cd agencia
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install --prefer-binary -r requirements.txt
```

> Se aparecer erro "Failed building wheel for pydantic-core":
> ```powershell
> pip install --only-binary :all: pydantic pydantic-core
> pip install fastapi "uvicorn[standard]" httpx PyJWT pika
> ```

### 5.7 - Subir as 3 agencias

> SEMPRE use `python -m uvicorn` (nao so `uvicorn`) e sempre defina RABBITMQ_URL primeiro.

```powershell
# Terminal 1 - Agencia 0
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload
```

```powershell
# Terminal 2 - Agencia 1
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload
```

```powershell
# Terminal 3 - Agencia 2
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload
```

### 5.8 - Subir o frontend

```powershell
cd C:\Users\SeuUsuario\Desktop\iceibank\frontend
npm install
npm run dev
```

---

## ERROS COMUNS

| Erro | Causa | Solucao |
|---|---|---|
| [ERRO] Defina a variavel RABBITMQ_URL | RABBITMQ_URL nao foi definida antes de subir | Defina $env:RABBITMQ_URL="amqps://..." ANTES do uvicorn |
| Failed building wheel for pydantic-core | Python 3.13 ou 3.14 sem wheel | Instale Python 3.11, ou use pip install --prefer-binary |
| uvicorn nao reconhecido | uvicorn nao esta no PATH | Use python -m uvicorn em vez de uvicorn |
| Porta ja em uso | Servico ja rodando | taskkill /PID (netstat -ano \| findstr :4046).Trim().Split()[-1] /F |
| Conta nao encontrada | Servidor reiniciou (estado perdido) | Recrie contas com bootstrap + login |

---

## RESUMO RAPIDO - comandos do dia a dia

| O que fazer | Comando |
|---|---|
| Definir RabbitMQ | `$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"` |
| Subir agencia 0 | `$env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload` |
| Subir agencia 1 | `$env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload` |
| Subir agencia 2 | `$env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload` |
| Subir frontend | `cd frontend; npm run dev` |
| Ver logs | `cd agencia; python mesclar_logs.py` |
| API docs | http://localhost:4046/docs |
| Interface web local | http://localhost:5173 |
| Interface web deploy | https://iceibank.vercel.app (ou URL do Vercel) |

## IMPORTANTE - dados somem ao reiniciar

As contas ficam apenas na memoria RAM. Se fechar o uvicorn, todas as contas somem.
Isso e intencional nos Sprints 1 e 2. Persistencia em banco de dados e assunto do Sprint 4.