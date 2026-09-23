# ICEIBank - Guia de Execucao Completo

---

## PARTE 1 - Rodar na sua maquina (ja configurada)

### 1.1 - Subir o backend (3 agencias)

Abra 3 terminais separados, todos dentro da pasta `agencia`:

```powershell
# Terminal 1 - Agencia 0
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload
```

```powershell
# Terminal 2 - Agencia 1
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload
```

```powershell
# Terminal 3 - Agencia 2
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload
```

> Dica: sempre use `python -m uvicorn` (mais robusto que chamar `uvicorn` direto)

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

- id 0, 3, 6, 9 ... -> Agencia 0 (porta 4046)
- id 1, 4, 7, 10 ... -> Agencia 1 (porta 4047)
- id 2, 5, 8, 11 ... -> Agencia 2 (porta 4048)

---

## PARTE 3 - Criar contas e usar via terminal

### 3.1 - Bootstrap (criar acesso) e Login

```powershell
# Criar acesso para conta 0 na agencia 0
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/bootstrap" `
  -ContentType "application/json" -Body '{"idConta":0,"senha":"minha123"}'

# Fazer login e guardar o token na variavel $tk0
$tk0 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4046/auth/login" `
  -ContentType "application/json" -Body '{"idConta":0,"senha":"minha123"}').token
```

### 3.2 - Criar mais contas

```powershell
# Conta 3 (agencia 0)
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"id":3,"nomeAluno":"Pedro","saldoInicial":300,"senha":"pedro123"}'

# Conta 1 (agencia 1) - bootstrap + login na agencia 1 primeiro
Invoke-RestMethod -Method Post -Uri "http://localhost:4047/auth/bootstrap" `
  -ContentType "application/json" -Body '{"idConta":1,"senha":"maria123"}'
$tk1 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4047/auth/login" `
  -ContentType "application/json" -Body '{"idConta":1,"senha":"maria123"}').token
Invoke-RestMethod -Method Post -Uri "http://localhost:4047/contas" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk1"} `
  -Body '{"id":1,"nomeAluno":"Maria","saldoInicial":200,"senha":"maria123"}'

# Conta 2 (agencia 2)
Invoke-RestMethod -Method Post -Uri "http://localhost:4048/auth/bootstrap" `
  -ContentType "application/json" -Body '{"idConta":2,"senha":"joao123"}'
$tk2 = (Invoke-RestMethod -Method Post -Uri "http://localhost:4048/auth/login" `
  -ContentType "application/json" -Body '{"idConta":2,"senha":"joao123"}').token
Invoke-RestMethod -Method Post -Uri "http://localhost:4048/contas" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk2"} `
  -Body '{"id":2,"nomeAluno":"Joao","saldoInicial":150,"senha":"joao123"}'
```

### 3.3 - Consultar saldo

```powershell
Invoke-RestMethod -Uri "http://localhost:4046/contas/0" -Headers @{Authorization="Bearer $tk0"}
Invoke-RestMethod -Uri "http://localhost:4046/contas/3" -Headers @{Authorization="Bearer $tk0"}
Invoke-RestMethod -Uri "http://localhost:4047/contas/1" -Headers @{Authorization="Bearer $tk1"}
```

### 3.4 - Depositar

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas/0/depositar" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"valor":100}'
```

### 3.5 - Sacar

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/contas/0/sacar" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"valor":50}'
```

### 3.6 - Transferencia local (mesma agencia)

```powershell
# Conta 0 -> Conta 3 (ambas na agencia 0)
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"idOrigem":0,"idDestino":3,"valor":50}'
```

### 3.7 - Transferencia entre agencias

```powershell
# Conta 0 (agencia 0) -> Conta 1 (agencia 1)
Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" `
  -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
  -Body '{"idOrigem":0,"idDestino":1,"valor":30}'

# Confirmar que Maria recebeu
Invoke-RestMethod -Uri "http://localhost:4047/contas/1" -Headers @{Authorization="Bearer $tk1"}
```

### 3.8 - Reproduzir a falha conhecida (evidencia do Sprint 4)

```powershell
# 1. Feche o terminal da agencia 1 (Ctrl+C no Terminal 2)
# 2. Tente transferir para conta 1 com agencia 1 fora do ar:
try {
  Invoke-RestMethod -Method Post -Uri "http://localhost:4046/transferencias" `
    -ContentType "application/json" -Headers @{Authorization="Bearer $tk0"} `
    -Body '{"idOrigem":0,"idDestino":1,"valor":20}'
} catch { $_.ErrorDetails.Message }
# Resultado esperado: HTTP 502 - debito aplicado, credito nao chegou
```

### 3.9 - Linha do tempo unificada

```powershell
cd C:\Users\Nicolas\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
python mesclar_logs.py
```

### 3.10 - Health-check (sem login)

```powershell
Invoke-RestMethod -Uri "http://localhost:4046/status"
Invoke-RestMethod -Uri "http://localhost:4047/status"
Invoke-RestMethod -Uri "http://localhost:4048/status"
```

### 3.11 - Testar token invalido (evidencia Parte F)

```powershell
# Sem token -> 401
try { Invoke-RestMethod -Uri "http://localhost:4046/contas/0" } catch { $_.ErrorDetails.Message }

# Token invalido -> 401
try { Invoke-RestMethod -Uri "http://localhost:4046/contas/0" `
  -Headers @{Authorization="Bearer token.invalido.aqui"} } catch { $_.ErrorDetails.Message }
```

---

## PARTE 4 - Usar pelo frontend (http://localhost:5173)

1. Selecione a agencia correta para a conta que quer acessar
2. Digite o ID da conta e a senha
3. Clique em Entrar
4. Use as abas na barra lateral: Saldo / Depositar / Sacar / Transferir
5. Clique em "Status / Lamport" para ver o relogio de Lamport atual

Conta 0 -> agencia http://localhost:4046
Conta 1 -> agencia http://localhost:4047
Conta 2 -> agencia http://localhost:4048
Conta 3 -> agencia http://localhost:4046
Conta 4 -> agencia http://localhost:4047

---

## PARTE 5 - Instalar e rodar do ZERO em maquina nova (Windows)

### 5.1 - Instalar Git

1. Acesse: https://git-scm.com/download/win
2. Baixe e execute o instalador (opcoes padrao estao otimas)
3. Verifique abrindo o PowerShell:

```powershell
git --version
# Deve aparecer: git version 2.x.x
```

### 5.2 - Instalar Python

> IMPORTANTE: instale a versao 3.11 ou 3.12 (NAO a 3.13).
> O Python 3.13 pode causar falha ao instalar o pydantic-core em computadores sem Rust.

1. Acesse: https://www.python.org/downloads/release/python-3119/
2. Role ate o final da pagina e baixe "Windows installer (64-bit)"
3. Execute o instalador
4. CRITICO: marque "Add Python to PATH" antes de clicar em Install Now
5. Verifique:

```powershell
python --version
# Deve aparecer: Python 3.11.x ou Python 3.12.x
pip --version
```

### 5.3 - Instalar Node.js

1. Acesse: https://nodejs.org/
2. Baixe a versao LTS (botao verde recomendado)
3. Execute o instalador (opcoes padrao)
4. Verifique:

```powershell
node --version
npm --version
```

### 5.4 - Habilitar execucao de scripts no PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Se perguntar: responda S (Sim) ou A (Sim para todos)
```

### 5.5 - Clonar o repositorio

```powershell
cd C:\Users\SeuUsuario\Desktop
git clone https://github.com/niicolasps/iceibank.git
cd iceibank
```

Substitua SeuUsuario pelo seu nome de usuario do Windows.

### 5.6 - Configurar o ambiente Python (backend)

```powershell
cd agencia

# Criar o ambiente virtual isolado
python -m venv .venv

# Ativar o ambiente virtual
.venv\Scripts\Activate.ps1
# O prompt deve mudar para: (.venv) PS ...

# Atualizar o pip antes de instalar (passo obrigatorio)
python -m pip install --upgrade pip

# Instalar as dependencias com preferencia por binarios pre-compilados
# (evita erro de compilacao do pydantic-core)
pip install --prefer-binary -r requirements.txt
```

> Se ainda aparecer erro "Failed building wheel for pydantic-core", use esse comando alternativo:
>
> ```powershell
> pip install --only-binary :all: pydantic pydantic-core
> pip install fastapi "uvicorn[standard]" httpx PyJWT
> ```

```powershell
# Verificar que instalou corretamente
pip show fastapi uvicorn httpx PyJWT pydantic
# Deve listar os 5 pacotes sem nenhum WARNING de "not found"
```

### 5.7 - Subir as 3 agencias

> IMPORTANTE: use sempre `python -m uvicorn` em vez de so `uvicorn`.
> Em laboratorios, o comando `uvicorn` sozinho pode nao ser reconhecido pelo PowerShell
> mesmo com o pacote instalado. O `python -m uvicorn` sempre funciona.

Abra 3 janelas do PowerShell. Em cada uma, rode:

```powershell
# Janela 1 - Agencia 0
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload
```

```powershell
# Janela 2 - Agencia 1
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload
```

```powershell
# Janela 3 - Agencia 2
cd C:\Users\SeuUsuario\Desktop\iceibank\agencia
.venv\Scripts\Activate.ps1
$env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload
```

Quando aparecer isso em cada janela, esta funcionando:
  INFO: Uvicorn running on http://0.0.0.0:4046 (Press CTRL+C to quit)

### 5.8 - Configurar e subir o frontend

```powershell
# Janela 4
cd C:\Users\SeuUsuario\Desktop\iceibank\frontend

# Instalar dependencias do Node (so uma vez)
npm install

# Subir o servidor React
npm run dev
```

Quando aparecer isso, esta funcionando:
  VITE v5.x  ready in 300ms
  Local: http://localhost:5173/

### 5.9 - Criar a primeira conta e fazer o primeiro login

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
- Agencia: http://localhost:4046
- ID: 0
- Senha: teste123

---

## ERROS COMUNS E SOLUCOES

| Erro | Causa | Solucao |
|---|---|---|
| Failed building wheel for pydantic-core | Python muito novo (3.13) sem wheel disponivel | Instale Python 3.11 ou 3.12, ou use `pip install --prefer-binary -r requirements.txt` |
| uvicorn nao reconhecido como cmdlet | uvicorn nao esta no PATH do sistema | Use `python -m uvicorn` em vez de `uvicorn` |
| WinError 10013 ao subir agencia | Porta ja em uso | `taskkill /PID (netstat -ano \| findstr :4046).Trim().Split()[-1] /F` |
| Token nao fornecido | Requisicao sem header Authorization | Refaca o login e guarde o token em `$tk` |
| Conta nao encontrada | Servidor foi reiniciado (estado perdido) | Recrie as contas com os comandos da Parte 3 |
| Impossivel conectar ao servidor remoto | Agencia de destino esta fora do ar | Suba os 3 terminais do backend |

---

## RESUMO RAPIDO - comandos do dia a dia

| O que fazer | Comando |
|---|---|
| Ativar venv | `.venv\Scripts\Activate.ps1` |
| Subir agencia 0 | `$env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload` |
| Subir agencia 1 | `$env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload` |
| Subir agencia 2 | `$env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload` |
| Subir frontend | `cd frontend; npm run dev` |
| Ver logs unificados | `cd agencia; python mesclar_logs.py` |
| Documentacao interativa API | http://localhost:4046/docs |
| Interface web | http://localhost:5173 |

## IMPORTANTE - contas somem ao reiniciar o servidor

As contas ficam apenas na memoria RAM. Se fechar e reabrir o uvicorn,
todas as contas somem e precisam ser recriadas com os comandos da Parte 3.
Isso e intencional no Sprint 1. Persistencia em banco de dados e assunto do Sprint 4.