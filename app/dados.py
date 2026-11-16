"""Camada de dados do app: tudo que lê ou grava no banco passa por aqui."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

BANCO = Path(__file__).resolve().parent.parent / "data" / "zelacidade.db"

TIPOS = {
    "buraco": "Buraco na via",
    "rachadura": "Rachadura em estrutura",
    "calcada_quebrada": "Calçada quebrada",
}
STATUS = {
    "aberto": "Aberto",
    "revisao_humana": "Revisão humana",
    "resolvido": "Resolvido",
}


def _conectar() -> sqlite3.Connection:
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BANCO)
    con.execute(
        """CREATE TABLE IF NOT EXISTS chamados (
            id_foto TEXT PRIMARY KEY,
            data_hora TEXT,
            tipo TEXT,
            confianca REAL,
            endereco TEXT,
            bairro TEXT,
            status TEXT
        )"""
    )
    return con


def listar_chamados() -> pd.DataFrame:
    with _conectar() as con:
        df = pd.read_sql_query("SELECT * FROM chamados ORDER BY data_hora DESC", con)
    df["tipo_nome"] = df["tipo"].map(TIPOS).fillna(df["tipo"])
    df["status_nome"] = df["status"].map(STATUS).fillna(df["status"])
    return df


def registrar_chamado(tipo: str, endereco: str, bairro: str, confianca: float | None = None) -> str:
    """Grava um chamado vindo do app e devolve o id gerado."""
    if tipo not in TIPOS:
        raise ValueError(f"Tipo inválido: {tipo}")
    if not endereco.strip():
        raise ValueError("Endereço é obrigatório")
    agora = datetime.now()
    id_foto = "APP" + agora.strftime("%Y%m%d%H%M%S")
    with _conectar() as con:
        con.execute(
            "INSERT INTO chamados VALUES (?,?,?,?,?,?,?)",
            (id_foto, agora.strftime("%Y-%m-%d %H:%M"), tipo, confianca,
             endereco.strip(), bairro.strip(), "aberto"),
        )
    return id_foto


def atualizar_status(id_foto: str, status: str) -> None:
    if status not in STATUS:
        raise ValueError(f"Status inválido: {status}")
    with _conectar() as con:
        con.execute("UPDATE chamados SET status = ? WHERE id_foto = ?", (status, id_foto))
