# GUIA DE EXECUCAO -- ICEIBank Sprint 2

---

# PARTE A -- DEMONSTRACAO PARA O PROFESSOR (DEPLOY NA NUVEM)

Use esta parte no computador do laboratorio.
Nao precisa instalar nada. So navegador e PowerShell.

---

## A.1 -- Acordar as agencias (2 minutos antes de mostrar)

As agencias no Render dormem quando ficam sem uso.
Abra estas 3 abas no navegador e espere cada uma responder:

  https://iceibank-agencia-0.onrender.com/status
  https://iceibank-agencia-1.onrender.com/status
  https://iceibank-agencia-2.onrender.com/status

O que deve aparecer: agencia: 0, relogioVetorialAtual: [0,0,0], quantidadeContas: 0

>> ATENCAO: pode demorar ate 60 segundos.
>> Se aparecer Service Unavailable, aguarde 30s e recarregue.

---

## A.2 -- Criar as contas (PowerShell -- ja vem no Windows)

Abra o PowerShell (tecla Windows, PowerShell, Enter). Cole cada linha:

    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-0.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":0,"senha":"demo123"}'
    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-1.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":1,"senha":"demo123"}'
    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-2.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":2,"senha":"demo123"}'

Deve aparecer: Conta X criada com senha.
Se aparecer Conta ja existe: normal, pode continuar.

---

## A.3 -- Abrir o frontend

Abra no navegador a URL do Vercel do projeto.
  - Agencia: Agencia 0 (Render)
  - ID da Conta: 0 | Senha: demo123
  - Clique em Acessar Conta

---

## A.4 -- ROTEIRO DE DEMONSTRACAO PARA O PROFESSOR

### Demo 1 -- Operacoes basicas e relogio vetorial subindo

PASSO 1: Frontend > Depositar | ID: 0, Valor: 500 > Confirmar
PASSO 2: Consultar Saldo | ID: 0 -- deve mostrar R$ 500,00
PASSO 3: Nova aba: https://iceibank-agencia-0.onrender.com/status
  Observe relogioVetorialAtual -- deve mostrar [2, 0, 0]

  O que explica para o professor:
  Cada operacao avanca o relogio vetorial. Comecou em [0,0,0]
  e agora esta em [2,0,0]: fizemos 2 operacoes.

---

### Demo 2 -- Relogio Vetorial em acao (transferencia entre agencias)

ANTES -- anote os vetores:
  https://iceibank-agencia-0.onrender.com/status  (ex: [2, 0, 0])
  https://iceibank-agencia-1.onrender.com/status  (ex: [0, 0, 0])

TRANSFERENCIA no frontend:
  Transferencia | ID Origem: 0 | ID Destino: 1 | Valor: 100 > Confirmar
  Mensagem esperada: Transferencia publicada para a agencia de destino

DEPOIS -- recarregue os status:
  Agencia 0: vetor mudou para ex: [4, 0, 0]
    (subiu: registrou o debito e o envio da mensagem)
  Aguarde 3 segundos. Agencia 1: vetor mudou para ex: [4, 1, 0]
    (absorveu o vetor da Ag0 e incrementou o proprio)

  O que explica para o professor:
  A Agencia 1 tem 4 na posicao 0: ela sabe tudo que Ag0 fez ate o evento 4.
  O relogio vetorial sincronizou as duas via mensagem RabbitMQ.

---

### Demo 3 -- Como ler o vetor

Exemplo: Agencia 1 com vetor [4, 1, 0]
  Posicao 0 = 4  -> Ag1 sabe que Ag0 fez 4 eventos
  Posicao 1 = 1  -> Ag1 fez 1 evento proprio (processar o credito)
  Posicao 2 = 0  -> Ag1 nunca viu nada da Ag2

---

### Demo 4 -- Alerta de Saldo Baixo (funcionalidade adicional)

Frontend > Sacar | ID: 0, Valor: 460 > Confirmar (saldo fica abaixo R$ 50)
Sistema publica automaticamente agencia.0.alerta-saldo-baixo no RabbitMQ.
Voce pode ver no CloudAMQP Manager: https://www.cloudamqp.com/

---

---

### Demo 5 -- Linha do tempo causal (mesclar_logs.py)

Abra o PowerShell e rode:

    cd C:\Users\Nicolas\Desktop\iceibank\agencia
    Write-Host "Executado em: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
    python mesclar_logs.py

O que deve aparecer:

1. SECAO "Linha do tempo (ordenada por hora de parede)":
   Lista todos os eventos de todas as agencias em ordem cronologica.
   Cada linha mostra: [agencia] vetor=[x,y,z] TIPO_EVENTO {detalhes}

   Exemplo:
     [agencia-0] vetor=[1, 0, 0] DEPOSITO {"id": 0, "valor": 500.0}
     [agencia-1] vetor=[0, 1, 0] DEPOSITO {"id": 1, "valor": 300.0}

2. SECAO "Pares de eventos CONCORRENTES entre agencias diferentes":
   Lista os pares de eventos que aconteceram de forma INDEPENDENTE,
   sem relacao causal entre si.

   Exemplo de par concorrente (o que explica para o professor):
     [agencia-0] DEPOSITO ([1, 0, 0]) x [agencia-1] DEPOSITO ([0, 1, 0])

   Por que sao concorrentes?
   A Agencia 0 nao sabia nada da Agencia 1 (posicao 1 do seu vetor = 0).
   A Agencia 1 nao sabia nada da Agencia 0 (posicao 0 do seu vetor = 0).
   Sao depositos independentes, sem relacao de causa e efeito.

3. O par de TRANSFERENCIA nao aparece na lista de concorrentes:
   [agencia-0] TRANSFERENCIA_DEBITO ([2, 0, 0]) -- nao esta na lista
   [agencia-1] TRANSFERENCIA_CREDITO_REMOTO ([3, 2, 0]) -- nao esta na lista

   Por que NAO sao concorrentes?
   [2,0,0] <= [3,2,0] em todas as posicoes (2<=3, 0<=2, 0<=0).
   O DEBITO aconteceu ANTES do CREDITO -- existe relacao causal.
   O script detectou isso corretamente.

  O que explica para o professor:
  "O script compara os vetores de todos os pares de eventos entre agencias
  diferentes. Se nenhum vetor domina o outro componente a componente,
  os eventos sao CONCORRENTES: aconteceram sem se influenciar. Se um vetor
  e menor ou igual ao outro em TODAS as posicoes, ha relacao causal.
  Isso e impossivel de determinar com o Relogio de Lamport (numero unico)."

---

## A.5 -- Demonstracao via PowerShell (API diretamente)

    $base0 = "https://iceibank-agencia-0.onrender.com"
    $base1 = "https://iceibank-agencia-1.onrender.com"
    $tk0 = (Invoke-RestMethod -Method Post -Uri "$base0/auth/login" -ContentType "application/json" -Body '{"idConta":0,"senha":"demo123"}').token
    Invoke-RestMethod -Method Post -Uri "$base0/contas/0/depositar" -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} -Body '{"valor":500}'
    Write-Host "=== VETOR ANTES ==="
    Invoke-RestMethod -Uri "$base0/status"
    Invoke-RestMethod -Uri "$base1/status"
    Invoke-RestMethod -Method Post -Uri "$base0/transferencias" -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} -Body '{"idOrigem":0,"idDestino":1,"valor":50}'
    Start-Sleep -Seconds 3
    Write-Host "=== VETOR DEPOIS ==="
    Invoke-RestMethod -Uri "$base0/status"
    Invoke-RestMethod -Uri "$base1/status"

---

## A.6 -- O QUE E O RELOGIO VETORIAL (para entender e explicar)

### O problema que ele resolve

3 agencias em cidades diferentes, cada uma no seu computador.
Cada maquina tem seu proprio relogio e podem estar dessincronizados.
O relogio vetorial ordena eventos SEM depender do relogio fisico.

### Como funciona

Cada agencia mantem um PLACAR com 3 numeros (um por agencia):
  Agencia 0: [0, 0, 0]
  Agencia 1: [0, 0, 0]
  Agencia 2: [0, 0, 0]

REGRA 1 -- Evento local (depositar, sacar):
  Soma +1 no proprio numero.
  Agencia 0 deposita --> [1, 0, 0]
  Agencia 0 saca     --> [2, 0, 0]

REGRA 2 -- Enviar transferencia:
  Soma +1 e manda o placar inteiro junto com a mensagem.
  Agencia 0 envia --> placar [4, 0, 0] vai junto

REGRA 3 -- Receber mensagem:
  Fica com o MAIOR de cada posicao. Depois soma +1 no proprio.
  Ag1 recebe [4, 0, 0] com placar [0, 0, 0]:
  -> max(0,4)=4, max(0,0)=0, max(0,0)=0 --> [4, 0, 0]
  -> +1 na posicao 1 --> [4, 1, 0]

### O que o vetor nos diz

V1 = [3, 1, 0] e V2 = [3, 2, 0]:
  3<=3, 1<=2, 0<=0 -- V1 inteiramente <= V2
  -> V1 aconteceu ANTES de V2

V1 = [3, 0, 0] e V2 = [0, 2, 0]:
  3<=0? NAO. Nao da para ordenar.
  -> Sao CONCORRENTES (aconteceram sem se influenciar)

### Por que e melhor que o Lamport (Sprint 1)?

Lamport usava UM NUMERO. A=5 e B=7: sabia que 5<7, mas nao sabia se
A causou B ou se foram eventos independentes em agencias diferentes.
O Vetorial determina isso com certeza matematica.

---

# LINKS RAPIDOS -- DEPLOY

  Frontend (Vercel):   https://iceibank.vercel.app
  Status Agencia 0:    https://iceibank-agencia-0.onrender.com/status
  Status Agencia 1:    https://iceibank-agencia-1.onrender.com/status
  Status Agencia 2:    https://iceibank-agencia-2.onrender.com/status
  API Docs Agencia 0:  https://iceibank-agencia-0.onrender.com/docs
  GitHub:              https://github.com/niicolasaps/iceibank
  CloudAMQP:           https://www.cloudamqp.com/

---

# PARTE B -- RODAR LOCALMENTE E INSTALAR DO ZERO

> O conteudo abaixo e o guia original completo com todos os comandos
> para rodar na sua maquina ou instalar do zero no laboratorio.

---

﻿# ICEIBank - Guia de Execucao Completo (Sprint 2)

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
