"""
routes.py — Roteador central do ICEIBank (Sprint 4)
Equivalente ao routes.js do exemplo Node.js/Express do roteiro.

- Rotas publicas de contas/transferencias: protegidas por JWT (como nos Sprints 1-3).
- GET /bully/lider e GET /status: publicos (o app Flutter consulta /bully/lider).
- Rotas internas (/bully/eleicao, /bully/coordenador, /2pc/*): protegidas pelo segredo
  compartilhado `x-token-interno` (dependencia `autenticacao_interna`), sem JWT.
  Ficam em protocolo_controller.py.
"""

from fastapi import APIRouter

from src.controllers.auth_controller import router as auth_router
from src.controllers.contas_controller import router as contas_router
from src.controllers.protocolo_controller import router as protocolo_router
from src.controllers.status_controller import router as status_router
from src.controllers.transferencias_controller import router as transferencias_router

router = APIRouter()

# Auth — login e registro de senha (sem JWT obrigatorio)
router.include_router(auth_router)

# Contas — CRUD + sincronizar offline-first (protegido por JWT)
router.include_router(contas_router)

# Transferencias (protegido por JWT)
router.include_router(transferencias_router)

# Health-check publico (/status)
router.include_router(status_router)

# Bully (/bully/lider publico; eleicao/coordenador internos) e 2PC (internos)
router.include_router(protocolo_router)
