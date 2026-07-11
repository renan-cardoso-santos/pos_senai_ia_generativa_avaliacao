"""Autenticação: cadastro, login e hash de senha.

A senha NUNCA é salva em texto puro — guarda-se um hash. Usamos PBKDF2-HMAC
(hashlib.pbkdf2_hmac) da biblioteca padrão, com salt aleatório por usuário,
para não depender de pacotes externos.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from app import db

_ITERACOES = 120_000


def hash_senha(senha: str, salt: bytes | None = None) -> str:
    """Gera 'salt_hex$hash_hex'. Salt novo se não fornecido."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, _ITERACOES)
    return f"{salt.hex()}${dk.hex()}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    """Confere a senha contra o valor 'salt_hex$hash_hex' salvo."""
    try:
        salt_hex, _ = armazenado.split("$")
    except ValueError:
        return False
    calculado = hash_senha(senha, bytes.fromhex(salt_hex))
    # Comparação em tempo constante.
    return hmac.compare_digest(calculado, armazenado)


def cadastrar(email: str, senha: str, nome: str = "") -> tuple[bool, str]:
    """Cria o usuário. Retorna (ok, mensagem)."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Informe um e-mail válido."
    if len(senha) < 8:
        return False, "A senha precisa ter ao menos 8 caracteres."
    if db.buscar_usuario_por_email(email):
        return False, "Já existe uma conta com esse e-mail."
    db.criar_usuario(email, hash_senha(senha), nome)
    return True, "Conta criada com sucesso. Faça login."


def login(email: str, senha: str) -> dict | None:
    """Valida credenciais. Retorna dados do usuário (dict) ou None."""
    usuario = db.buscar_usuario_por_email(email)
    if usuario and verificar_senha(senha, usuario["senha_hash"]):
        return {"id": usuario["id"], "email": usuario["email"], "nome": usuario["nome"]}
    return None
