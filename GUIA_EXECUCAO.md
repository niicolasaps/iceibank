# GUIA DE EXECUCAO -- ICEIBank

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

O que deve aparecer em cada aba:
  agencia: 0, relogioVetorialAtual: [0,0,0], quantidadeContas: 0

>> ATENCAO: pode demorar ate 60 segundos na primeira vez.
>> Se aparecer "Service Unavailable", aguarde 30 segundos e recarregue.

---

## A.2 -- Criar as contas

Abra o PowerShell (tecla Windows, digite PowerShell, Enter).
Cole cada comando abaixo (um de cada vez):

    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-0.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":0,"senha":"demo123"}'

    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-1.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":1,"senha":"demo123"}'

    Invoke-RestMethod -Method Post -Uri "https://iceibank-agencia-2.onrender.com/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":2,"senha":"demo123"}'

Deve aparecer: "Conta X criada com senha." para cada uma.
Se aparecer "Conta ja existe": normal, pode continuar.

---

## A.3 -- Abrir o frontend

Abra no navegador a URL do Vercel do projeto.

Na tela de login:
  - Agencia: selecione "Agencia 0 (Render)"
  - ID da Conta: 0
  - Senha: demo123
  - Clique em "Acessar Conta"

---

## A.4 -- ROTEIRO DE DEMONSTRACAO

### Demo 1 -- Operacoes basicas e relogio vetorial subindo

PASSO 1: No frontend, clique em Depositar
  - ID da conta: 0, Valor: 500, Clique em Confirmar

PASSO 2: Clique em Consultar Saldo
  - ID: 0 -- deve mostrar R$ 500,00

PASSO 3: Abra nova aba: https://iceibank-agencia-0.onrender.com/status
  Observe o campo "relogioVetorialAtual" -- deve mostrar [2, 0, 0]

  O que explica para o professor:
  "Cada operacao avanca o relogio vetorial da agencia.
  Comecou em [0,0,0] e agora esta em [2,0,0]: fizemos 2 operacoes."

---

### Demo 2 -- Relogio Vetorial em acao (transferencia entre agencias)

ANTES DA TRANSFERENCIA -- anote os vetores:

  Agencia 0: https://iceibank-agencia-0.onrender.com/status
  Anote o relogioVetorialAtual, ex: [2, 0, 0]

  Agencia 1: https://iceibank-agencia-1.onrender.com/status
  Anote o relogioVetorialAtual, ex: [0, 0, 0]

FAZER A TRANSFERENCIA no frontend:
  - Clique em Transferencia
  - ID Origem: 0 | ID Destino: 1 | Valor: 100
  - Clique em Confirmar
  - Mensagem: "Transferencia publicada para a agencia de destino"

DEPOIS DA TRANSFERENCIA -- recarregue os status:

  Agencia 0 (recarregue a aba do status):
  -> vetor mudou, ex: [4, 0, 0]
  (subiu porque registrou o debito e o envio da mensagem)

  Aguarde 3 segundos. Agencia 1 (recarregue):
  -> vetor mudou, ex: [4, 1, 0]
  (absorveu o vetor da Agencia 0 e incrementou o proprio)

  O que explica:
  "A Agencia 1 agora conhece o historico da Agencia 0.
  O vetor dela tem 4 na posicao 0: ela viu tudo que Ag0 fez ate o evento 4.
  O relogio vetorial sincronizou as duas via mensagem RabbitMQ."

---

### Demo 3 -- Como ler o vetor

Exemplo: Agencia 1 com vetor [4, 1, 0]

  Posicao 0 = 4  -> A Agencia 1 sabe que a Agencia 0 fez 4 eventos
  Posicao 1 = 1  -> A Agencia 1 fez 1 evento proprio (processar o credito)
  Posicao 2 = 0  -> A Agencia 1 nunca viu nada da Agencia 2

---

### Demo 4 -- Alerta de Saldo Baixo (funcionalidade adicional)

No frontend, Sacar -- ID: 0, Valor: 460 (deixa saldo abaixo de R$ 50)
O sistema publica automaticamente "agencia.0.alerta-saldo-baixo" no RabbitMQ.
Voce pode ver no CloudAMQP Manager: https://www.cloudamqp.com/

---

## A.5 -- Demonstracao via PowerShell (mostrar a API diretamente)

     = "https://iceibank-agencia-0.onrender.com"
     = "https://iceibank-agencia-1.onrender.com"

     = (Invoke-RestMethod -Method Post -Uri "/auth/login" -ContentType "application/json" -Body '{"idConta":0,"senha":"demo123"}').token

    Invoke-RestMethod -Method Post -Uri "/contas/0/depositar" -ContentType "application/json" -Headers @{Authorization="Bearer "} -Body '{"valor":500}'

    Write-Host "=== VETOR ANTES ==="
    Invoke-RestMethod -Uri "/status"
    Invoke-RestMethod -Uri "/status"

    Invoke-RestMethod -Method Post -Uri "/transferencias" -ContentType "application/json" -Headers @{Authorization="Bearer "} -Body '{"idOrigem":0,"idDestino":1,"valor":50}'

    Start-Sleep -Seconds 3

    Write-Host "=== VETOR DEPOIS ==="
    Invoke-RestMethod -Uri "/status"
    Invoke-RestMethod -Uri "/status"

---

## A.6 -- O QUE E O RELOGIO VETORIAL

### O problema que ele resolve

3 agencias em cidades diferentes, cada uma em seu proprio computador.
Cada computador tem seu proprio relogio e podem estar dessincronizados.
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
  Soma +1 e manda o placar inteiro junto.
  Agencia 0 envia --> [4, 0, 0], esse vetor vai junto na mensagem

REGRA 3 -- Receber mensagem:
  Fica com o MAIOR de cada posicao. Depois soma +1 no proprio.
  Agencia 1 recebe [4, 0, 0] com seu placar [0, 0, 0]:
  -> max de cada posicao: [4, 0, 0]
  -> +1 na posicao 1: [4, 1, 0]

### O que o vetor nos diz

V1 = [3, 1, 0] e V2 = [3, 2, 0]:
  3<=3, 1<=2, 0<=0 -- todos de V1 sao <= aos de V2
  -> V1 aconteceu ANTES de V2

V1 = [3, 0, 0] e V2 = [0, 2, 0]:
  3<=0? NAO. Entao nao da para ordenar.
  -> Sao CONCORRENTES (aconteceram sem se influenciar)

### Por que e melhor que o Lamport (Sprint 1)?

Lamport usava UM NUMERO. Se A=5 e B=7, sabia que 5<7, mas nao sabia
se A causou B ou se foram eventos independentes em agencias diferentes.
O Vetorial determina isso com certeza matematica.

---

# PARTE B -- RODAR LOCALMENTE (sua maquina)

IMPORTANTE: SEMPRE defina RABBITMQ_URL antes de subir cada agencia.

Terminal 1 -- Agencia 0:
  cd C:\Users\Nicolas\Desktop\iceibank\agencia
  .venv\Scripts\Activate.ps1
  ="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
  ="0"; python -m uvicorn src.main:app --port 4046 --reload

Terminal 2 -- Agencia 1:
  ="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
  ="1"; python -m uvicorn src.main:app --port 4047 --reload

Terminal 3 -- Agencia 2:
  ="amqps://spwydfzs:XDNv5s6vOLAFD1ekPvSU8EBUoJiztP1W@jackal.rmq.cloudamqp.com/spwydfzs"
  ="2"; python -m uvicorn src.main:app --port 4048 --reload

Frontend:
  cd C:\Users\Nicolas\Desktop\iceibank\frontend
  npm run dev
  Abra: http://localhost:5173

Criar contas:
  Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":0,"senha":"demo123"}'
  Invoke-RestMethod -Method Post -Uri "http://localhost:4047/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":1,"senha":"demo123"}'
  Invoke-RestMethod -Method Post -Uri "http://localhost:4048/auth/bootstrap" -ContentType "application/json" -Body '{"idConta":2,"senha":"demo123"}'

---

# PARTE C -- INSTALAR DO ZERO (laboratorio)

1. Python 3.11: https://www.python.org/downloads/release/python-3119/
   -> marque "Add Python to PATH"

2. Node.js: https://nodejs.org/ -> versao LTS

3. Clonar:
   cd C:\Users\SeuUsuario\Desktop
   git clone https://github.com/niicolasaps/iceibank.git
   cd iceibank

4. Configurar Python:
   cd agencia
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install --prefer-binary -r requirements.txt

5. Habilitar scripts (se necessario):
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

6. Subir agencias -- igual ao B acima, trocando o caminho

---

# ERROS COMUNS

  [ERRO] Defina a variavel RABBITMQ_URL
  -> Cole ="amqps://..." e rode de novo

  Impossivel conectar-se ao servidor
  -> Agencia nao esta rodando. Verifique os terminais.

  Credenciais invalidas
  -> Servidor reiniciou. Rode o bootstrap de novo.

  Conta ja existe
  -> Normal. Pode ignorar e continuar.

  Service Unavailable no Render
  -> Aguarde 60 segundos e recarregue.

  Failed building wheel for pydantic-core
  -> Instale Python 3.11.

  uvicorn nao reconhecido
  -> Use python -m uvicorn

---

# LINKS RAPIDOS

  Frontend (Vercel):   https://iceibank.vercel.app
  Status Agencia 0:    https://iceibank-agencia-0.onrender.com/status
  Status Agencia 1:    https://iceibank-agencia-1.onrender.com/status
  Status Agencia 2:    https://iceibank-agencia-2.onrender.com/status
  API Docs:            https://iceibank-agencia-0.onrender.com/docs
  GitHub:              https://github.com/niicolasaps/iceibank
  CloudAMQP:           https://www.cloudamqp.com/
