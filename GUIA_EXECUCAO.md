# GUIA DE EXECUCAO -- ICEIBank Sprint 3

---

# PARTE A -- DEMONSTRACAO PARA O PROFESSOR (DEPLOY NA NUVEM + APP MOBILE)

Use esta parte no computador do laboratorio ou na sua apresentacao.
As Demonstracoes 1 a 5 podem ser feitas na nuvem (Render + Vercel) apenas com navegador e PowerShell.
As Demonstracoes 6 a 10 (Sprint 3: Bully com failover ao vivo, App Flutter e Offline-First) tambem tem os comandos prontos tanto para nuvem quanto localmente.

---

## A.1 -- Acordar as agencias no Render (2 minutos antes de mostrar)

As agencias no Render dormem quando ficam sem uso.
Abra estas 3 abas no navegador e espere cada uma responder:

  https://iceibank-agencia-0.onrender.com/status
  https://iceibank-agencia-1.onrender.com/status
  https://iceibank-agencia-2.onrender.com/status

E confira tambem a eleicao de lider (Sprint 3) nas 3:

  https://iceibank-agencia-0.onrender.com/bully/lider
  https://iceibank-agencia-1.onrender.com/bully/lider
  https://iceibank-agencia-2.onrender.com/bully/lider

O que deve aparecer em `/bully/lider`: `{"idAgencia": X, "liderAtual": 2}` (todas concordando com a Agencia 2 como lider).

>> ATENCAO: pode demorar ate 60 segundos para acordar o free tier do Render.
>> Se aparecer Service Unavailable, aguarde 30s e recarregue.

---

## A.2 -- Criar as contas (PowerShell -- ja vem no Windows)

Abra o PowerShell (tecla Windows, PowerShell, Enter). Cole cada linha:

    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-0.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":0,"senha":"demo123"}'
    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-1.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":1,"senha":"demo123"}'
    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-2.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":2,"senha":"demo123"}'

Deve aparecer: `Conta X criada com senha.`
Se aparecer `Senha da conta X definida com sucesso`: normal, pode continuar.

---

## A.3 -- Abrir o frontend web (Vercel)

Abra no navegador: https://iceibank.vercel.app
  - Agencia: Agencia 0 (Render)
  - ID da Conta: 0 | Senha: demo123
  - Clique em Acessar Conta

---

## A.4 -- ROTEIRO DE DEMONSTRACAO PARA O PROFESSOR (Sprints 1, 2 e 3)

### Demo 1 -- Operacoes basicas e relogio vetorial subindo (Sprints 1 e 2)

PASSO 1: Frontend > Depositar | ID: 0, Valor: 500 > Confirmar
PASSO 2: Consultar Saldo | ID: 0 -- deve mostrar R$ 500,00 (e o endpoint agora devolve `vetorAtual` junto!)
PASSO 3: Nova aba: https://iceibank-agencia-0.onrender.com/status
  Observe `relogioVetorialAtual` avançando a cada evento.

---

### Demo 2 -- Relogio Vetorial + RabbitMQ em acao (Sprint 2)

TRANSFERENCIA no frontend:
  Transferencia | ID Origem: 0 | ID Destino: 1 | Valor: 100 > Confirmar
  Mensagem esperada: `Transferencia publicada para a agencia de destino (entrega assincrona).`

Recarregue `/status` nas agencias 0 e 1 apos 3 segundos:
  A Agencia 1 absorveu o vetor da Agencia 0 via RabbitMQ (`max` componente a componente + 1 na propria posicao).

---

### Demo 3 -- Eleicao de Lider com Algoritmo de Bully (Sprint 3 - Parte A)

No PowerShell (funciona no Render ou em `http://localhost:4046..4048`):

    Get-Date
    Invoke-RestMethod -Uri "http://localhost:4046/bully/lider" -Method Get
    Invoke-RestMethod -Uri "http://localhost:4047/bully/lider" -Method Get
    Invoke-RestMethod -Uri "http://localhost:4048/bully/lider" -Method Get

  O que explica para o professor:
  "Ao subir, cada agencia dispara `iniciar_eleicao()` em background enviando `POST /bully/eleicao`
  para as agencias de ID maior. Como a Agencia 2 tem o maior ID ativo, ninguem maior responde a ela;
  ela vence, se declara `TORNOU_LIDER` e anuncia `POST /bully/coordenador` para as agencias 0 e 1.
  Todas as 3 convergem para `liderAtual = 2`."

---

### Demo 4 -- Heartbeat e Failover Automatico (Sprint 3 - Parte B)

PASSO 1: No Terminal 3 (Agencia 2, porta 4048), aperte `Ctrl+C` para derrubar a lider.
PASSO 2: Aguarde ~4 segundos (o heartbeat roda a cada 3 segundos por padrao, com timeout de 1s).
PASSO 3: Consulte as duas agencias vivas:

    Get-Date
    Invoke-RestMethod -Uri "http://localhost:4046/bully/lider" -Method Get
    Invoke-RestMethod -Uri "http://localhost:4047/bully/lider" -Method Get

  Resultado esperado: ambas agora mostram `liderAtual = 1` automaticamente!
  Nos terminais das agencias 0 e 1 aparece `LIDER_NAO_RESPONDEU`, seguido de nova eleicao e `TORNOU_LIDER` na Agencia 1.

PASSO 4: Suba a Agencia 2 novamente no Terminal 3. Em poucos segundos ela inicia eleicao ao subir e retoma a lideranca (`liderAtual = 2`).

---

### Demo 5 -- Historico de Liderancas (Sprint 3 - Parte C)

No PowerShell:

    cd C:\Users\Nicolas\Desktop\iceibank\agencia
    Get-Date
    .\.venv\Scripts\python.exe historico_lideranca.py

  O que deve aparecer:
  1. `=== Histórico de eventos de eleição ===`: todos os eventos `ELEICAO_INICIADA`, `ELEICAO_RECEBIDA`, `TORNOU_LIDER`, `LIDER_ANUNCIADO` e `LIDER_NAO_RESPONDEU` das 3 agencias ordenados por `horaParede`.
  2. `=== Linha do tempo de líderes ===`: mostra a sequencia exata de quem assumiu a lideranca na subida inicial (0 -> 1 -> 2), no failover apos a queda da 2 (-> 1) e na volta da 2 (-> 2).

---

### Demo 6 -- Funcionalidade Adicional Sprint 3: Timeout e Heartbeat Configuraveis

Suba uma agencia definindo `BULLY_HEARTBEAT_MS` e `BULLY_TIMEOUT_MS` por variavel de ambiente (e mostre tambem a validacao de valor invalido):

    $env:BULLY_HEARTBEAT_MS="1000"
    $env:BULLY_TIMEOUT_MS="abc"
    $env:AGENCIA_ID="2"
    .\.venv\Scripts\python.exe -m uvicorn src.main:app --port 4048

  Aparece no console:
    `[Bully] AVISO: BULLY_TIMEOUT_MS='abc' invalido (esperado inteiro > 0, em ms). Usando padrao 1000 ms.`
    `[Bully] Configuracao: heartbeat=1000 ms, timeout=1000 ms`

---

### Demo 7 -- Sincronizacao Offline-First e Conflito HTTP 409 no Backend (Sprint 3 - Parte E)

No PowerShell, simule o app lendo o vetor, uma mudanca externa acontecendo na conta e o backend rejeitando a sincronizacao desatualizada com HTTP 409:

    Invoke-RestMethod -Uri "http://localhost:4046/auth/bootstrap" -Method Post -ContentType "application/json" -Body '{"idConta":0,"senha":"1234"}'
    $tok = (Invoke-RestMethod -Uri "http://localhost:4046/auth/login" -Method Post -ContentType "application/json" -Body '{"idConta":0,"senha":"1234"}').token
    $h = @{ Authorization = "Bearer $tok" }

    # 1. App consulta saldo e guarda o vetorAtual conhecido
    $conta = Invoke-RestMethod -Uri "http://localhost:4046/contas/0" -Headers $h
    $vAntigo = $conta.vetorAtual
    Write-Host "Vetor guardado pelo app: $($vAntigo -join ', ')"

    # 2. Mudanca acontece na agencia enquanto o app estava offline
    Invoke-RestMethod -Uri "http://localhost:4046/contas/0/depositar" -Method Post -Headers $h -ContentType "application/json" -Body '{"valor":100}'

    # 3. App tenta sincronizar operacao pendente usando o vetor antigo -> recebe HTTP 409!
    Get-Date
    $body = @{ tipo = "DEPOSITO"; valor = 10; vetorConhecido = $vAntigo } | ConvertTo-Json
    try {
      Invoke-RestMethod -Uri "http://localhost:4046/contas/0/sincronizar" -Method Post -Headers $h -ContentType "application/json" -Body $body
    } catch {
      Write-Host "HTTP $($_.Exception.Response.StatusCode.value__)"
      $_.ErrorDetails.Message
    }

  O que explica para o professor:
  "A agencia compara `vetorConhecido` com `vetorAtual` usando `comparar_vetores()` dentro de um lock atomico (`with relogio.travar():`). Como o vetor avancou (relacao != IGUAIS), ela recusa aplicar as cegas e devolve HTTP 409 com `vetorConhecido`, `vetorAtual` e `contaAtual`."

---

### Demo 8 -- App Flutter Mobile: Fluxo Bancario, Painel da Lider e Modo Offline-First (Sprint 3 - Partes D e F)

1. **Login e Fluxo Bancario:** entre no app no emulador Android com Conta `0` e Senha `1234`. Mostre o saldo, faca um deposito, um saque e uma transferencia.
2. **Painel de Lideranca + Failover na Tela:** aponte para o painel no topo mostrando `Lider Atual: Agencia 2`. Derrube a Agencia 2 no terminal (`Ctrl+C`) sem tocar no celular: em ~3 a 6 segundos o painel atualiza sozinho na tela para `Lider Atual: Agencia 1`.
3. **Modo Offline-First + UI Otimista:** ative o **Modo Aviao** no emulador. O banner offline aparece. Faca um deposito de R$ 50: ele nao falha — entra na lista `Operacoes feitas offline` como **Pendente**, e o saldo muda para **Saldo Provisorio** em dourado/laranja mostrando tambem o saldo confirmado abaixo.
4. **Sincronizacao Automatica ao Reconectar:** desligue o Modo Aviao sem clicar em nada no app. Em poucos segundos a fila sincroniza sozinha, o item pendente some e o saldo confirmado passa a valer.
5. **Conflito 409 Visivel na Tela do App:** ative o Modo Aviao, faca um deposito de R$ 20 no app e, antes de reconectar, faca um deposito direto na conta 0 pelo PowerShell (ou frontend web). Desative o Modo Aviao: o app recebe 409, atualiza o saldo para o valor real da agencia e exibe o card vermelho **CONFLITO** com os botoes **"Aplicar mesmo assim"** e **"Descartar"**.

---

# LINKS RAPIDOS -- DEPLOY

  Frontend (Vercel):   https://iceibank.vercel.app
  Status Agencia 0:    https://iceibank-agencia-0.onrender.com/status
  Status Agencia 1:    https://iceibank-agencia-1.onrender.com/status
  Status Agencia 2:    https://iceibank-agencia-2.onrender.com/status
  Lider Agencia 0:     https://iceibank-agencia-0.onrender.com/bully/lider
  Lider Agencia 1:     https://iceibank-agencia-1.onrender.com/bully/lider
  Lider Agencia 2:     https://iceibank-agencia-2.onrender.com/bully/lider
  API Docs Agencia 0:  https://iceibank-agencia-0.onrender.com/docs
  GitHub:              https://github.com/niicolasaps/iceibank
  CloudAMQP:           https://www.cloudamqp.com/

---

# PARTE B -- RODAR LOCALMENTE E INSTALAR DO ZERO (SPRINT 3 COMPLETO)

> Guia completo com todos os comandos para rodar o Backend (3 agencias), Frontend Web e App Mobile Flutter na sua maquina ou instalar do zero.

---

## PARTE 1 - Rodar na sua maquina (ja configurada)

### 1.1 - Subir o backend (3 agencias com RabbitMQ + Bully)

Abra 3 terminais PowerShell separados. Em CADA UM, defina `RABBITMQ_URL` antes de subir:

```powershell
# Terminal 1 - Agencia 0 (porta 4046)
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.\.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="0"
.\.venv\Scripts\python.exe -m uvicorn src.main:app --port 4046
```

```powershell
# Terminal 2 - Agencia 1 (porta 4047)
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.\.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="1"
.\.venv\Scripts\python.exe -m uvicorn src.main:app --port 4047
```

```powershell
# Terminal 3 - Agencia 2 (porta 4048)
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.\.venv\Scripts\Activate.ps1
$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
$env:AGENCIA_ID="2"
.\.venv\Scripts\python.exe -m uvicorn src.main:app --port 4048
```

*(Opcional - Funcionalidade Adicional Sprint 3: defina `$env:BULLY_HEARTBEAT_MS="3000"` e `$env:BULLY_TIMEOUT_MS="1000"` antes do uvicorn se quiser customizar os tempos do Bully).*

### 1.2 - Criar as contas iniciais (Bootstrap)

Como o armazenamento das agencias e em memoria RAM, crie as contas 0, 1 e 2 apos subir os servidores:

```powershell
# Terminal 4
Invoke-RestMethod -Uri "http://localhost:4046/auth/bootstrap" -Method Post -ContentType "application/json" -Body '{"idConta":0,"senha":"1234"}'
Invoke-RestMethod -Uri "http://localhost:4047/auth/bootstrap" -Method Post -ContentType "application/json" -Body '{"idConta":1,"senha":"1234"}'
Invoke-RestMethod -Uri "http://localhost:4048/auth/bootstrap" -Method Post -ContentType "application/json" -Body '{"idConta":2,"senha":"1234"}'
```

### 1.3 - Subir o frontend web (React / Vite)

```powershell
# Terminal 4
cd C:\Users\Nicolas\Desktop\iceibank\frontend
npm run dev
# Abre em http://localhost:5173
```

### 1.4 - Subir o App Mobile Flutter no Emulador Android

```powershell
# Terminal 5
# 1. Garanta que o Flutter esta no PATH da sessao (caso nao esteja global):
$env:Path += ";C:\flutter\flutter\bin"

# 2. Inicie o emulador Android (ou abra pelo Android Studio -> Virtual Device Manager):
flutter emulators --launch Pixel_9_Pro

# 3. Aguarde o emulador ligar completamente e rode o app:
cd C:\Users\Nicolas\Desktop\iceibank\app_mobile
flutter run -d emulator-5554
```

> **Nota sobre rede no Android:** o arquivo `app_mobile/lib/config.dart` ja vem configurado com `http://10.0.2.2:4046` (4047 e 4048), que e o IP especial do emulador Android que aponta para o `localhost` do Windows. Se for rodar em **celular fisico via USB**, troque pelo IP Wi-Fi do seu PC em `config.dart` e suba o `uvicorn` com `--host 0.0.0.0`.

---

## PARTE 2 - Regra de particionamento de contas

A agencia responsavel por uma conta e: `id % 3`

- `id 0, 3, 6 ...` -> Agencia 0 (porta `4046`)
- `id 1, 4, 7 ...` -> Agencia 1 (porta `4047`)
- `id 2, 5, 8 ...` -> Agencia 2 (porta `4048`)

---

## PARTE 3 - Scripts de Observabilidade (Sprints 2 e 3)

```powershell
cd C:\Users\Nicolas\Desktop\iceibank\agencia

# Linha do tempo causal e deteccao de eventos concorrentes via Relogio Vetorial (Sprint 2):
.\.venv\Scripts\python.exe mesclar_logs.py

# Historico de eventos de eleicao Bully e linha do tempo de lideres (Sprint 3):
.\.venv\Scripts\python.exe historico_lideranca.py
```

---

## PARTE 4 - Instalar e rodar do ZERO em maquina nova

### 4.1 - Pre-requisitos

1. **Git:** https://git-scm.com/download/win
2. **Python 3.11 (64-bit):** https://www.python.org/downloads/release/python-3119/ (marque *"Add Python to PATH"*). Evite Python 3.13+ na criacao da venv para nao precisar compilar `pydantic-core`.
3. **Node.js LTS:** https://nodejs.org/
4. **Flutter SDK + Android Studio:**
   - Extraia o Flutter SDK em `C:\flutter` e adicione `C:\flutter\bin` (ou `C:\flutter\flutter\bin`) ao `PATH` do usuario.
   - No Android Studio: **SDK Manager -> SDK Tools** -> marque **Android SDK Command-line Tools (latest)** e **NDK (Side by side) 28.2.13676358**.
   - Em **Virtual Device Manager**, crie um emulador Android (ex.: Pixel 9 Pro).
   - Confira tudo com `flutter doctor`.

### 4.2 - Clonar e instalar dependencias

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

cd C:\Users\SeuUsuario\Desktop
git clone https://github.com/niicolasaps/iceibank.git
cd iceibank

# 1. Backend Python
cd agencia
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install --prefer-binary -r requirements.txt

# 2. Frontend Web React
cd ..\frontend
npm install

# 3. App Mobile Flutter
cd ..\app_mobile
flutter pub get
```

---

## ERROS COMUNS E SOLUCOES

| Erro | Causa | Solucao |
|---|---|---|
| `No module named uvicorn` | Chamou o `python` global (3.13) em vez do Python da `.venv` | Use `.\.venv\Scripts\python.exe -m uvicorn ...` ou ative `.venv\Scripts\Activate.ps1` |
| `[ERRO] Defina a variavel RABBITMQ_URL` | `RABBITMQ_URL` nao foi definida no terminal atual | Defina `$env:RABBITMQ_URL="amqps://..."` antes de subir o `uvicorn` |
| `'idna' codec can't encode character` | `RABBITMQ_URL` ficou com placeholder `amqps://...` | Use a URL completa real da instancia CloudAMQP |
| `'flutter' nao e reconhecido` | Pasta do SDK do Flutter fora do PATH | Adicione `C:\flutter\flutter\bin` ao PATH do usuario ou rode `$env:Path += ";C:\flutter\flutter\bin"` |
| `Android sdkmanager did not install NDK 28.2.13676358` | NDK exigido pelos plugins nao instalado no Android SDK | Android Studio -> SDK Manager -> SDK Tools -> Show Package Details -> NDK 28.2.13676358 |
| `Conta nao encontrada nesta agencia` | As agencias reiniciaram (dados em memoria RAM) ou conta de outra particao | Rode o `/auth/bootstrap` na agencia correta (`id % 3`) |

---

## RESUMO RAPIDO - Comandos do dia a dia

| O que fazer | Comando |
|---|---|
| Definir RabbitMQ | `$env:RABBITMQ_URL="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"` |
| Subir agencia 0 | `$env:AGENCIA_ID="0"; .\.venv\Scripts\python.exe -m uvicorn src.main:app --port 4046` |
| Subir agencia 1 | `$env:AGENCIA_ID="1"; .\.venv\Scripts\python.exe -m uvicorn src.main:app --port 4047` |
| Subir agencia 2 | `$env:AGENCIA_ID="2"; .\.venv\Scripts\python.exe -m uvicorn src.main:app --port 4048` |
| Consultar lider Bully | `Invoke-RestMethod -Uri "http://localhost:4046/bully/lider"` |
| Historico de lideres | `cd agencia; .\.venv\Scripts\python.exe historico_lideranca.py` |
| Linha do tempo causal | `cd agencia; .\.venv\Scripts\python.exe mesclar_logs.py` |
| Subir frontend web | `cd frontend; npm run dev` |
| Rodar app Flutter | `cd app_mobile; flutter run -d emulator-5554` |
