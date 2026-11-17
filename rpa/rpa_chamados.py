"""RPA de chamados do ZelaCidade.

Fluxo:
1. Lê as detecções da visão computacional (CSV) com Pandas.
2. Limpa e valida os dados (tipos, duplicatas, confiança fora do intervalo, endereço vazio).
3. Grava os chamados válidos num banco SQLite.
4. Gera um e-mail de resumo para a prefeitura (arquivo .eml; envio real só com SMTP configurado).

Uso:
    python rpa/rpa_chamados.py [caminho_do_csv]
"""

from __future__ import annotations

import logging
import os
import smtplib
import sqlite3
import sys
import time
from email.message import EmailMessage
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CSV_PADRAO = RAIZ / "data" / "deteccoes_exemplo.csv"
BANCO = RAIZ / "data" / "zelacidade.db"
SAIDA = Path(__file__).resolve().parent / "saida"

TIPOS_VALIDOS = {"buraco", "rachadura", "calcada_quebrada", "desgaste_asfalto"}
CONFIANCA_MINIMA = 0.60  # abaixo disso o chamado vai para revisão humana

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("rpa")


def ler_deteccoes(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(caminho, dtype=str)
    log.info("Lidas %d linhas de %s", len(df), caminho.name)
    return df


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (validos, rejeitados), cada rejeitado com o motivo."""
    df = df.copy()
    df["tipo"] = df["tipo"].str.strip().str.lower()
    df["confianca"] = pd.to_numeric(df["confianca"].str.replace(",", ".", regex=False), errors="coerce")
    df["endereco"] = df["endereco"].fillna("").str.strip()
    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")

    motivos = pd.Series("", index=df.index)
    motivos[df.duplicated(subset=["data_hora", "tipo", "endereco"], keep="first")] = "duplicado"
    motivos[(motivos == "") & ~df["tipo"].isin(TIPOS_VALIDOS)] = "tipo desconhecido"
    motivos[(motivos == "") & df["confianca"].isna()] = "confiança ausente"
    motivos[(motivos == "") & ~df["confianca"].between(0, 1)] = "confiança fora de 0–1"
    motivos[(motivos == "") & (df["endereco"] == "")] = "endereço vazio"
    motivos[(motivos == "") & df["data_hora"].isna()] = "data inválida"

    rejeitados = df[motivos != ""].assign(motivo=motivos[motivos != ""])
    validos = df[motivos == ""].copy()
    validos["status"] = validos["confianca"].apply(
        lambda c: "aberto" if c >= CONFIANCA_MINIMA else "revisao_humana"
    )
    log.info("%d válidos, %d rejeitados", len(validos), len(rejeitados))
    return validos, rejeitados


def gravar(validos: pd.DataFrame, banco: Path) -> int:
    banco.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(banco) as con:
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
        antes = con.execute("SELECT COUNT(*) FROM chamados").fetchone()[0]
        linhas = validos.assign(data_hora=validos["data_hora"].dt.strftime("%Y-%m-%d %H:%M"))[
            ["id_foto", "data_hora", "tipo", "confianca", "endereco", "bairro", "status"]
        ].itertuples(index=False)
        con.executemany("INSERT OR IGNORE INTO chamados VALUES (?,?,?,?,?,?,?)", linhas)
        depois = con.execute("SELECT COUNT(*) FROM chamados").fetchone()[0]
    novos = depois - antes
    log.info("%d chamados novos gravados em %s", novos, banco.name)
    return novos


def montar_email(validos: pd.DataFrame, rejeitados: pd.DataFrame) -> EmailMessage:
    por_tipo = validos.groupby("tipo").size().to_dict()
    revisao = int((validos["status"] == "revisao_humana").sum())
    corpo = [
        "Resumo automático de chamados do ZelaCidade.",
        "",
        f"Chamados válidos: {len(validos)}",
        *[f"  - {tipo}: {qtd}" for tipo, qtd in sorted(por_tipo.items())],
        f"Aguardando revisão humana (confiança < {CONFIANCA_MINIMA:.0%}): {revisao}",
        f"Registros rejeitados na validação: {len(rejeitados)}",
        "",
        "Lista de chamados abertos:",
        *[
            f"  {r.id_foto} | {r.tipo} | {r.endereco} ({r.bairro})"
            for r in validos[validos["status"] == "aberto"].itertuples()
        ],
        "",
        "Mensagem gerada automaticamente. Dados simulados para fins acadêmicos.",
    ]
    msg = EmailMessage()
    msg["Subject"] = f"ZelaCidade – {len(validos)} chamados registrados"
    msg["From"] = os.getenv("ZELA_EMAIL_DE", "zelacidade@exemplo.com")
    msg["To"] = os.getenv("ZELA_EMAIL_PARA", "zeladoria@prefeitura.exemplo")
    msg.set_content("\n".join(corpo))
    return msg


def enviar_ou_salvar(msg: EmailMessage, tentativas: int = 3) -> Path | None:
    """Envia por SMTP se ZELA_SMTP_HOST estiver configurado; senão salva o .eml."""
    host = os.getenv("ZELA_SMTP_HOST")
    if host:
        for n in range(1, tentativas + 1):
            try:
                with smtplib.SMTP(host, int(os.getenv("ZELA_SMTP_PORT", "587")), timeout=10) as s:
                    s.starttls()
                    s.login(os.environ["ZELA_SMTP_USER"], os.environ["ZELA_SMTP_SENHA"])
                    s.send_message(msg)
                log.info("E-mail enviado para %s", msg["To"])
                return None
            except Exception as erro:  # noqa: BLE001 - registrar e tentar de novo
                log.warning("Falha no envio (tentativa %d/%d): %s", n, tentativas, erro)
                time.sleep(2 * n)
        log.error("Envio falhou; salvando o e-mail em arquivo")
    SAIDA.mkdir(exist_ok=True)
    arquivo = SAIDA / f"email_{time.strftime('%Y%m%d_%H%M%S')}.eml"
    arquivo.write_bytes(bytes(msg))
    log.info("E-mail salvo em %s", arquivo.relative_to(RAIZ))
    return arquivo


def main(caminho_csv: Path = CSV_PADRAO) -> None:
    df = ler_deteccoes(caminho_csv)
    validos, rejeitados = limpar(df)
    gravar(validos, BANCO)
    SAIDA.mkdir(exist_ok=True)
    rejeitados.to_csv(SAIDA / "rejeitados.csv", index=False, encoding="utf-8-sig")
    enviar_ou_salvar(montar_email(validos, rejeitados))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else CSV_PADRAO)
