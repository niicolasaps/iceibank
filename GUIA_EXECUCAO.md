# ICEIBank — Guia de Execução Completo

---

## PARTE 1 — Rodar na sua máquina (já configurada)

### 1.1 — Subir o backend (3 agências)

Abra 3 terminais separados, todos dentro da pasta `agencia`:

```powershell
# Terminal 1 — Agência 0
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="0"; uvicorn src.main:app --port 4046 --reload
```

```powershell
# Terminal 2 — Agência 1
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="1"; uvicorn src.main:app --port 4047 --reload
```

```powershell
# Terminal 3 — Agência 2
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="2"; uvicorn src.main:app --port 4048 --reload
```

### 1.2 — Subir o frontend (interface web)

```powershell
# Terminal 4
cd C:\Users\Nicolas\Desktop\iceibank\frontend
npm run dev
# Abre em http://localhost:5173
```

---

## PARTE 2 — Regra de particionamento de contas

A agência responsável por uma conta é: id % 3

- id 0, 3, 6, 9 ... → Agência 0 (porta 4046)
- id 1, 4, 7, 10 ... → Agência 1 (porta 4047)
- id 2, 5, 8, 11 ... → Agência 2 (porta 4048)

---

## PARTE 3 — Criar contas e usar via terminal

### 3.1 — Bootstrap (criar acesso) e Login

```powershell
# Criar acesso para conta 0 na agência 0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/bootstrap" `
  -ContentType "application/json" -Body '{"idConta":0,"senha":"minha123"}'

# Fazer login e guardar o token na variável $tk0
$tk0 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/login" `
  -ContentType "application/json" -Body '{"idConta":0,"senha":"minha123"}').token
```

### 3.2 — Criar mais contas

```powershell
# Conta 3 (agência 0) — id 3 porque 3%3=0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"id":3,"nomeAluno":"Pedro","saldoInicial":300,"senha":"pedro123"}'

# Conta 1 (agência 1) — bootstrap + login na agência 1 primeiro
Invoke-RestMethod -Method Post -Uri "http://localhost:4047/auth/bootstrap" `
  -ContentType "application/json" -Body '{"idConta":1,"senha":"maria123"}'
$tk1 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4047/auth/login" `
  -ContentType "application/json" -Body '{"idConta":1,"senha":"maria123"}').token
Invoke-RestMethod -Method Post -Uri "http://localhost:4047/contas" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk1"} `
  -Body '{"id":1,"nomeAluno":"Maria","saldoInicial":200,"senha":"maria123"}'

# Conta 2 (agência 2)
Invoke-RestMethod -Method Post -Uri "http://localhost:4048/auth/bootstrap" `
  -ContentType "application/json" -Body '{"idConta":2,"senha":"joao123"}'
$tk2 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4048/auth/login" `
  -ContentType "application/json" -Body '{"idConta":2,"senha":"joao123"}').token
Invoke-RestMethod -Method Post -Uri "http://localhost:4048/contas" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk2"} `
  -Body '{"id":2,"nomeAluno":"Joao","saldoInicial":150,"senha":"joao123"}'
```

### 3.3 — Consultar saldo

```powershell
Invoke-RestMethod -Uri "http://localhost:4046/contas/0" -Headers @{Authorization="Bearer $tk0"}
Invoke-RestMethod -Uri "http://localhost:4046/contas/3" -Headers @{Authorization="Bearer $tk0"}
Invoke-RestMethod -Uri "http://localhost:4047/contas/1" -Headers @{Authorization="Bearer $tk1"}
```

### 3.4 — Depositar

```powershell
# Depositar R$ 100 na conta 0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas/0/depositar" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"valor":100}'
```

### 3.5 — Sacar

```powershell
# Sacar R$ 50 da conta 0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas/0/sacar" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"valor":50}'
```

### 3.6 — Transferência local (mesma agência)

```powershell
# Conta 0 → Conta 3 (ambas na agência 0)
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"idOrigem":0,"idDestino":3,"valor":50}'
```

### 3.7 — Transferência entre agências

```powershell
# Conta 0 (agência 0) → Conta 1 (agência 1)
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"idOrigem":0,"idDestino":1,"valor":30}'

# Confirmar que Maria recebeu
Invoke-RestMethod -Uri "http://localhost:4047/contas/1" -Headers @{Authorization="Bearer $tk1"}
```

### 3.8 — Reproduzir a falha conhecida (evidência do Sprint 4)

```powershell
# 1. Feche o terminal da agência 1 (Ctrl+C no Terminal 2)
# 2. Tente transferir para conta 1 com agência 1 fora do ar:
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"idOrigem":0,"idDestino":1,"valor":20}'
# Resultado esperado: HTTP 502 — débito aplicado, crédito não chegou
```

### 3.9 — Linha do tempo unificada

```powershell
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
python mesclar_logs.py
```

### 3.10 — Health-check (sem login)

```powershell
Invoke-RestMethod -Uri "http://localhost:4046/status"
Invoke-RestMethod -Uri "http://localhost:4047/status"
Invoke-RestMethod -Uri "http://localhost:4048/status"
```

### 3.11 — Testar token inválido (evidência Parte F)

```powershell
# Sem token → 401
try { Invoke-RestMethod -Uri "http://localhost:4046/contas/0" } catch { $_.ErrorDetails.Message }

# Token inválido → 401
try { Invoke-RestMethod -Uri "http://localhost:4046/contas/0" `
  -Headers @{Authorization="Bearer token.invalido.aqui"} } catch { $_.ErrorDetails.Message }
```

---

## PARTE 4 — Usar pelo frontend (http://localhost:5173)

1. Selecione a agência correta para a conta que quer acessar
2. Digite o ID da conta e a senha
3. Clique em Entrar
4. Use as abas: Saldo / Depositar / Sacar / Transferir
5. Botão Status (canto superior direito) mostra o relógio de Lamport atual

Conta 0 → agência http://localhost:4046
Conta 1 → agência http://localhost:4047
Conta 2 → agência http://localhost:4048
Conta 3 → agência http://localhost:4046
Conta 4 → agência http://localhost:4047

---

## PARTE 5 — Instalar e rodar do ZERO em máquina nova (Windows)

### 5.1 — Instalar Git

1. Acesse: https://git-scm.com/download/win
2. Baixe e execute o instalador (opções padrão estão ótimas)
3. Verifique abrindo o PowerShell:

```powershell
git --version
# Deve aparecer: git version 2.x.x
```

### 5.2 — Instalar Python 3.13

1. Acesse: https://www.python.org/downloads/
2. Clique em Download Python 3.13.x (botão amarelo grande)
3. Execute o instalador
4. IMPORTANTE: marque a opção "Add Python to PATH" antes de clicar em Install Now
5. Verifique:

```powershell
python --version
# Deve aparecer: Python 3.13.x
pip --version
# Deve aparecer: pip 24.x ...
```

### 5.3 — Instalar Node.js

1. Acesse: https://nodejs.org/
2. Baixe a versão LTS (botão verde recomendado)
3. Execute o instalador (opções padrão)
4. Verifique:

```powershell
node --version
# Deve aparecer: v22.x.x
npm --version
# Deve aparecer: 10.x.x
```

### 5.4 — Habilitar execução de scripts no PowerShell (se necessário)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Responda: S (Sim)
```

### 5.5 — Clonar o repositório

```powershell
cd C:\Users\SeuUsuario\Desktop
git clone https://github.com/niicolasps/iceibank.git
cd iceibank
```

Substitua SeuUsuario pelo seu nome de usuário do Windows.

### 5.6 — Configurar o ambiente Python (backend)

```powershell
cd agencia

# Criar o ambiente virtual isolado
python -m venv .venv

# Ativar o ambiente virtual
.venv\Scripts\Activate.ps1
# O prompt deve mudar para: (.venv) PS ...

# Instalar todas as dependências
pip install -r requirements.txt

# Verificar que instalou (deve listar os pacotes sem erro)
pip show fastapi uvicorn httpx PyJWT pydantic
```

### 5.7 — Subir as 3 agências

Abra 3 janelas do PowerShell. Em cada uma, rode:

```powershell
# Janela 1 — Agência 0
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="0"; uvicorn src.main:app --port 4046 --reload
```

```powershell
# Janela 2 — Agência 1
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="1"; uvicorn src.main:app --port 4047 --reload
```

```powershell
# Janela 3 — Agência 2
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="2"; uvicorn src.main:app --port 4048 --reload
```

Quando aparecer isso em cada janela, está funcionando:
  [Agência 0] ouvindo na porta 4046
  INFO: Uvicorn running on http://0.0.0.0:4046

### 5.8 — Configurar e subir o frontend

```powershell
# Janela 4
cd C:\Users\SeuUsuario\Desktop\iceibank\frontend

# Instalar dependências do Node (só uma vez)
npm install

# Subir o servidor React
npm run dev
```

Quando aparecer isso, está funcionando:
  VITE v5.x  ready in 300ms
  Local: http://localhost:5173/

### 5.9 — Criar a primeira conta e fazer o primeiro login

```powershell
# Janela 5 (qualquer PowerShell)

# Criar acesso para conta 0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/bootstrap" `
  -ContentType "application/json" -Body '{"idConta":0,"senha":"teste123"}'

# Login
$tk = (Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/login" `
  -ContentType "application/json" -Body '{"idConta":0,"senha":"teste123"}').token

# Confirmar que funciona
Invoke-RestMethod -Uri "http://localhost:4046/status"
```

Agora abra http://localhost:5173 no navegador:
- Agência: http://localhost:4046
- ID: 0
- Senha: teste123

---

## RESUMO RÁPIDO — comandos do dia a dia

| O que fazer                  | Comando                                                              |
|------------------------------|----------------------------------------------------------------------|
| Ativar venv                  | .venv\Scripts\Activate.ps1                                          |
| Subir agência 0              | $env:AGENCIA_ID="0"; uvicorn src.main:app --port 4046 --reload      |
| Subir agência 1              | $env:AGENCIA_ID="1"; uvicorn src.main:app --port 4047 --reload      |
| Subir agência 2              | $env:AGENCIA_ID="2"; uvicorn src.main:app --port 4048 --reload      |
| Subir frontend               | cd frontend; npm run dev                                            |
| Ver logs unificados          | cd agencia; python mesclar_logs.py                                  |
| Documentação interativa API  | http://localhost:4046/docs                                          |
| Interface web                | http://localhost:5173                                               |
| Liberar porta travada (4046) | taskkill /PID (netstat -ano | findstr ":4046 ").Trim().Split()[-1] /F |

## IMPORTANTE — contas somem ao reiniciar o servidor

As contas ficam apenas na memória RAM. Se fechar e reabrir o uvicorn,
todas as contas somem e precisam ser recriadas com os comandos da Parte 3.
Isso é intencional no Sprint 1. Persistência em banco de dados é assunto do Sprint 4.