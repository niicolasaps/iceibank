"""
routes.py — Roteador central do ICEIBank
Equivalente ao routes.js do exemplo Node.js/Express do roteiro.
"""

from fastapi import APIRouter

from src.controllers.auth_controller import router as auth_router
from src.controllers.contas_controller import router as contas_router
from src.controllers.status_controller import router as status_router
from src.controllers.transferencias_controller import router as transferencias_router

router = APIRouter()

# Auth — login e registro de senha (sem JWT obrigatorio)
router.include_router(auth_router)

# Parte C — CRUD de contas (protegido por JWT)
router.include_router(contas_router)

# Parte D — Transferencias (protegido por JWT)
router.include_router(transferencias_router)

# Funcionalidade adicional — Health-check (publico)
router.include_router(status_router)
