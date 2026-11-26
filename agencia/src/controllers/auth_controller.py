"""
auth_controller.py — Endpoints de Autenticacao do ICEIBank (Parte F, Secao 11)
Atualizado no Sprint 4 para persistir mudancas de senha/bootstrap em `estado.salvar()`.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src import config
from src.services.auth import criar_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    idConta: int
    senha: str


class RegistrarSenhaBody(BaseModel):
    idConta: int
    senha: str


@router.post("/login")
def login(body: LoginBody, request: Request):
    """Autentica um usuario pelo id da conta e senha. Retorna um JWT com expiracao de 30 minutos."""
    estado = request.app.state.estado
    with estado.lock:
        conta = estado.contas.get(body.idConta)
        if conta is None or conta.get("senha") != body.senha:
            raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    token = criar_token({"sub": str(body.idConta), "idConta": body.idConta})
    return {"token": token}


@router.post("/registrar")
def registrar_senha(body: RegistrarSenhaBody, request: Request):
    """Cadastra (ou atualiza) a senha de uma conta existente (persistido em disco)."""
    estado = request.app.state.estado
    with estado.lock:
        conta = estado.contas.get(body.idConta)
        if conta is None:
            raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
        conta["senha"] = body.senha
        estado.salvar()
    return {"mensagem": f"Senha da conta {body.idConta} cadastrada com sucesso."}


@router.post("/bootstrap")
def bootstrap(body: RegistrarSenhaBody, request: Request):
    """
    Cria a senha de uma conta existente OU cria a conta com saldo 0, sem JWT.
    Persiste imediatamente no EstadoDuravel para sobreviver a `docker compose restart`.
    """
    estado = request.app.state.estado
    id_agencia = request.app.state.id_agencia

    with estado.lock:
        if body.idConta not in estado.contas:
            if config.agencia_responsavel(body.idConta) != id_agencia:
                raise HTTPException(400, detail=f"Conta {body.idConta} nao pertence a esta agencia.")
            nome = f"Usuario {body.idConta}"
            estado.contas[body.idConta] = {
                "id": body.idConta,
                "titular": nome,
                "nomeAluno": nome,
                "saldo": 0.0,
                "reservado": 0.0,
                "senha": body.senha,
            }
            estado.salvar()
            return {"mensagem": f"Conta {body.idConta} criada com senha. Use POST /contas para atualizar os dados apos o login."}

        estado.contas[body.idConta]["senha"] = body.senha
        estado.salvar()
        return {"mensagem": f"Senha da conta {body.idConta} definida com sucesso."}
