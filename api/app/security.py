"""Autenticação simples do MVP: chaves vindas de variáveis de ambiente.

Nenhuma chave tem valor padrão. Se a variável não estiver definida, o grupo
de endpoints correspondente responde 503, em vez de ficar aberto.
"""
from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def _check(env_name: str, received: str | None, what: str) -> None:
    expected = os.getenv(env_name, "")
    if not expected:
        raise HTTPException(status_code=503, detail=f"{what} não configurado neste ambiente.")
    if not received or not hmac.compare_digest(received.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Credencial ausente ou inválida.")


def robot_key(x_api_key: str | None = Header(default=None)) -> None:
    """Robô RPA (contrato docs/productApiContract.yaml)."""
    _check("ROBOT_API_KEY", x_api_key, "Acesso do robô")


def sensor_key(x_api_key: str | None = Header(default=None)) -> None:
    """Visão computacional e dispositivo ESP32."""
    _check("SENSOR_API_KEY", x_api_key, "Acesso dos sensores")


def hr_code(x_hr_code: str | None = Header(default=None)) -> None:
    """Área do RH. Substitui o login enquanto o MVP não tem autenticação de usuários."""
    _check("HR_ACCESS_CODE", x_hr_code, "Acesso do RH")
