"""
routes.py — Roteador central do ICEIBank
Equivalente ao routes.js do exemplo Node.js/Express do roteiro.

Neste sprint (Parte C), registra apenas as rotas de contas.
As rotas de transferência (Parte D) e autenticação (Parte F) serão adicionadas
nas próximas sessões — os comentários abaixo marcam onde elas serão incluídas.
"""

from fastapi import APIRouter

from src.controllers.contas_controller import router as contas_router

# Router raiz — equivalente ao express.Router() montado em '/' no app.js
router = APIRouter()

# Parte C — CRUD de contas
# Equivalente a:
#   router.post('/contas', contasController.criarConta)
#   router.get('/contas/:id', contasController.consultarSaldo)
#   router.post('/contas/:id/depositar', contasController.depositar)
#   router.post('/contas/:id/sacar', contasController.sacar)
router.include_router(contas_router)

# Parte D (Sprint 1, Semana 2) — transferências entre agências
# TODO: descomentar quando implementar
# from src.controllers.transferencias_controller import router as transferencias_router
# router.include_router(transferencias_router)
