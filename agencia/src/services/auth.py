"""
auth.py — Serviço de Autenticação JWT do ICEIBank (Parte F, Seção 11)

Biblioteca: PyJWT (mais simples e com menos dependências que python-jose)
Algoritmo: HS256 (HMAC-SHA256) — padrão para JWT com chave simétrica

Design de credenciais escolhido:
  - Cada conta tem uma senha cadastrada no momento da criação (campo "senha")
  - Login: POST /auth/login com {"idConta": N, "senha": "..."}
  - Expiração: 30 minutos (configurável via variável de ambiente JWT_EXP_MINUTOS)

Token de serviço (chamadas máquina-a-máquina entre agências):
  - Sub = "service", sem expiração (ou expiração longa)
  - Gerado no startup de main.py e armazenado em app.state.token_servico
  - Justificativa: creditar-remoto é uma chamada interna entre agências, não uma
    sessão de usuário humano. Usar um token de serviço separado evita que tokens
    de usuários precisem ser repassados entre backends.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SECRET_KEY = os.environ.get("JWT_SECRET", "iceibank-dev-secret-nao-usar-em-producao")
ALGORITMO = "HS256"
EXP_MINUTOS = int(os.environ.get("JWT_EXP_MINUTOS", "30"))

# Esquema Bearer — extrai o token do header Authorization: Bearer <token>
bearer_scheme = HTTPBearer(auto_error=False)


def criar_token(dados: dict, expira_em: Optional[timedelta] = None) -> str:
    """Gera um token JWT assinado com SECRET_KEY."""
    payload = dados.copy()
    expiracao = datetime.now(timezone.utc) + (expira_em or timedelta(minutes=EXP_MINUTOS))
    payload["exp"] = expiracao
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITMO)


def criar_token_servico() -> str:
    """Gera o token de serviço (máquina-a-máquina, validade longa)."""
    return criar_token({"sub": "service", "tipo": "servico"}, expira_em=timedelta(days=365))


def _decodificar(token: str) -> dict:
    """Decodifica e valida um token JWT; lança HTTPException 401 se inválido."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITMO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")


def get_usuario_atual(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """
    Dependência FastAPI para rotas protegidas de usuário.
    Rejeita tokens de serviço (sub="service") — usuário deve estar autenticado.
    """
    if creds is None:
        raise HTTPException(status_code=401, detail="Token não fornecido.")
    payload = _decodificar(creds.credentials)
    if payload.get("sub") == "service":
        raise HTTPException(status_code=401, detail="Token de serviço não autorizado aqui.")
    return payload


def get_token_qualquer(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """
    Dependência FastAPI para creditar-remoto: aceita token de usuário OU de serviço.
    Necessário porque a agência chamante envia o token de serviço, não um token de usuário.
    """
    if creds is None:
        raise HTTPException(status_code=401, detail="Token não fornecido.")
    return _decodificar(creds.credentials)
