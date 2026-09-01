"""
auth_controller.py — Endpoints de Autenticação do ICEIBank (Parte F, Seção 11)

POST /auth/login     — recebe idConta + senha, retorna JWT se válido
POST /auth/registrar — cadastra senha para conta existente (sem JWT — para setup inicial)

O endpoint /auth/registrar existe apenas para facilitar testes durante o sprint.
Em um sistema real, a senha seria definida na criação da conta ou via fluxo separado.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

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
    """
    Autentica um usuário pelo id da conta e senha.
    Retorna um JWT com expiração de 30 minutos.
    """
    contas = request.app.state.contas
    conta = contas.get(body.idConta)

    if conta is None or conta.get("senha") != body.senha:
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    token = criar_token({"sub": str(body.idConta), "idConta": body.idConta})
    return {"token": token}


@router.post("/registrar")
def registrar_senha(body: RegistrarSenhaBody, request: Request):
    """
    Cadastra (ou atualiza) a senha de uma conta existente.
    Não exige JWT — é o endpoint de setup inicial para testes.
    """
    contas = request.app.state.contas
    conta = contas.get(body.idConta)

    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")

    conta["senha"] = body.senha
    return {"mensagem": f"Senha da conta {body.idConta} cadastrada com sucesso."}
