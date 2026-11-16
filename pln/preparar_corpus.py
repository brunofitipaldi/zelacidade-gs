"""Preparação de corpus do ZelaCidade (PLN).

Lê documentos de vários formatos, limpa e normaliza o texto e gera três corpus
para fine-tuning de uma LLM de pequeno porte:

- texto_puro.jsonl            {"text": ..., "fonte": ...}
- perguntas_respostas.jsonl   {"pergunta": ..., "resposta": ..., "fonte": ...}
- conversacional.jsonl        {"messages": [{"role": ..., "content": ...}, ...]}

Cada corpus sai também dividido em treino/validação (90/10).

Uso:
    python pln/preparar_corpus.py [pasta_de_entrada] [pasta_de_saida]
Padrão: docs_fonte/ -> pln/corpus/
"""

from __future__ import annotations

import json
import random
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA_PADRAO = RAIZ / "docs_fonte"
SAIDA_PADRAO = Path(__file__).resolve().parent / "corpus"
FORMATOS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm"}

PROMPT_SISTEMA = (
    "Você é o assistente do ZelaCidade. Responda dúvidas sobre manutenção urbana, "
    "calçadas e serviços da prefeitura usando apenas os documentos oficiais. "
    "Se a informação não estiver nos documentos, diga que não sabe e indique o canal 156."
)

# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------


def extrair_paginas(caminho: Path) -> list[str]:
    """Devolve o texto bruto do arquivo, uma string por página (ou uma só)."""
    ext = caminho.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        return [p.extract_text() or "" for p in PdfReader(caminho).pages]
    if ext == ".docx":
        import docx

        d = docx.Document(caminho)
        linhas = []
        for p in d.paragraphs:
            texto = p.text.strip()
            if not texto:
                continue
            if p.style is not None and p.style.name.lower().startswith(("heading", "título")):
                texto = "# " + texto
            linhas.append(texto)
        return ["\n\n".join(linhas)]
    if ext in {".html", ".htm"}:
        from bs4 import BeautifulSoup

        sopa = BeautifulSoup(caminho.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        for tag in sopa(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        partes = []
        for el in sopa.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            texto = el.get_text(" ", strip=True)
            if texto:
                partes.append(("# " if el.name.startswith("h") else "") + texto)
        return ["\n\n".join(partes)]
    return [caminho.read_text(encoding="utf-8", errors="ignore")]


# ---------------------------------------------------------------------------
# Limpeza e normalização
# ---------------------------------------------------------------------------

LIGADURAS = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", " ": " ", " ": " ", "​": ""}
RE_PAGINA = re.compile(r"^\s*(p[áa]g(ina)?\.?\s*)?\d{1,4}(\s*(de|/)\s*\d{1,4})?\s*$", re.I)
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
RE_TELEFONE = re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b")


@dataclass
class Estatisticas:
    linhas_brutas: int = 0
    cabecalhos_rodapes: int = 0
    numeros_pagina: int = 0
    hifenizacoes: int = 0
    duplicados: int = 0
    curtos: int = 0
    dados_mascarados: Counter = field(default_factory=Counter)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto)
    for de, para in LIGADURAS.items():
        texto = texto.replace(de, para)
    texto = texto.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return texto


def remover_repetidas(paginas: list[str], est: Estatisticas) -> list[list[str]]:
    """Remove linhas que se repetem em várias páginas (cabeçalho/rodapé) e números de página."""
    linhas_por_pagina = [[l.strip() for l in p.splitlines()] for p in paginas]
    est.linhas_brutas += sum(len(l) for l in linhas_por_pagina)
    contagem = Counter(l for pag in linhas_por_pagina for l in set(pag) if l)
    limite = max(3, len(paginas) // 2) if len(paginas) >= 3 else None
    resultado = []
    for pag in linhas_por_pagina:
        mantidas = []
        for l in pag:
            if limite and l and contagem[l] >= limite and len(l) < 120:
                est.cabecalhos_rodapes += 1
                continue
            if RE_PAGINA.match(l):
                est.numeros_pagina += 1
                continue
            mantidas.append(l)
        resultado.append(mantidas)
    return resultado


def parece_titulo(linha: str) -> bool:
    if linha.startswith("#"):
        return True
    sem_numero = re.sub(r"^\d+(\.\d+)*[.)]?\s+", "", linha)
    curta = 3 <= len(sem_numero) <= 80
    sem_ponto_final = not sem_numero.endswith((".", ";", ",", ":"))
    return curta and sem_ponto_final and (sem_numero.isupper() or sem_numero.endswith("?") or sem_numero != linha)


def montar_secoes(linhas: list[str], est: Estatisticas) -> list[tuple[str, list[str]]]:
    """Junta linhas quebradas em parágrafos e agrupa parágrafos por título."""
    secoes: list[tuple[str, list[str]]] = [("Introdução", [])]
    atual: list[str] = []

    def fechar_paragrafo():
        if atual:
            secoes[-1][1].append(" ".join(atual))
            atual.clear()

    for linha in linhas:
        if not linha:
            fechar_paragrafo()
            continue
        if parece_titulo(linha):
            fechar_paragrafo()
            titulo = re.sub(r"^#+\s*", "", linha)
            titulo = re.sub(r"^\d+(\.\d+)*[.)]?\s+", "", titulo).strip()
            if titulo.isupper():
                titulo = titulo.capitalize()
            secoes.append((titulo, []))
            continue
        if atual and atual[-1].endswith("-") and linha[:1].islower():
            atual[-1] = atual[-1][:-1] + linha.split(" ", 1)[0]
            resto = linha.split(" ", 1)[1] if " " in linha else ""
            est.hifenizacoes += 1
            if resto:
                atual.append(resto)
            continue
        if linha.startswith(("- ", "• ", "* ", "– ")):
            fechar_paragrafo()
            atual.append(linha[2:].strip())
            fechar_paragrafo()
            continue
        atual.append(linha)
        if linha.endswith((".", "!", "?", ":")) and len(linha) < 60:
            fechar_paragrafo()
    fechar_paragrafo()
    return [(t, p) for t, p in secoes if p]


def mascarar(texto: str, est: Estatisticas) -> str:
    for rotulo, regex in (("[EMAIL]", RE_EMAIL), ("[CPF]", RE_CPF), ("[TELEFONE]", RE_TELEFONE)):
        texto, n = regex.subn(rotulo, texto)
        est.dados_mascarados[rotulo] += n
    return texto


def limpar_paragrafos(secoes, est: Estatisticas, vistos: set[str]):
    saida = []
    for titulo, paragrafos in secoes:
        limpos = []
        for p in paragrafos:
            p = re.sub(r"\s+", " ", p).strip()
            p = mascarar(p, est)
            if len(p) < 30:
                est.curtos += 1
                continue
            chave = re.sub(r"\W+", "", p.lower())
            if chave in vistos:
                est.duplicados += 1
                continue
            vistos.add(chave)
            limpos.append(p)
        if limpos:
            saida.append((titulo, limpos))
    return saida


# ---------------------------------------------------------------------------
# Geração dos corpus
# ---------------------------------------------------------------------------

RE_DEFINICAO = re.compile(r"^(?P<termo>[A-ZÀ-Ú][\wÀ-ú\s-]{2,40}?)\s+(?P<verbo>é|são)\s+(?P<resto>.{20,})$")
PRONOMES = {"ele", "ela", "eles", "elas", "isso", "isto", "este", "esta", "esse", "essa", "aquele", "aquela", "o", "a", "os", "as", "que", "não"}
RE_REGRA = re.compile(r"\b(deve|devem|é obrigatório|é obrigatória|é proibido|é proibida|não pode|não podem)\b", re.I)


def frases(paragrafo: str) -> list[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú])", paragrafo) if f.strip()]


def cortar(texto: str, limite: int = 700) -> str:
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0]
    return corte.rstrip(",;:") + "..."


def gerar_texto_puro(docs) -> list[dict]:
    registros = []
    for fonte, secoes in docs:
        for titulo, paragrafos in secoes:
            bloco = f"{titulo}\n\n"
            for p in paragrafos:
                if len(bloco) + len(p) > 1200 and bloco.strip() != titulo:
                    registros.append({"text": bloco.strip(), "fonte": fonte})
                    bloco = f"{titulo}\n\n"
                bloco += p + "\n\n"
            if bloco.strip() != titulo:
                registros.append({"text": bloco.strip(), "fonte": fonte})
    return registros


def gerar_perguntas(docs) -> list[dict]:
    pares = []
    for fonte, secoes in docs:
        nome = Path(fonte).stem.replace("_", " ")
        for titulo, paragrafos in secoes:
            # 1) Título da seção vira pergunta
            if titulo.endswith("?"):
                pergunta = titulo
            elif titulo != "Introdução":
                pergunta = f"O que o documento \"{nome}\" diz sobre {titulo[0].lower() + titulo[1:]}?"
            else:
                pergunta = None
            if pergunta:
                pares.append({"pergunta": pergunta, "resposta": cortar(" ".join(paragrafos[:2])),
                              "fonte": fonte, "origem": "titulo"})
            # 2) Definições do tipo "X é ..." (ignora frases que começam com pronome ou artigo
            #    e termos que já são o assunto do título da seção)
            for p in paragrafos:
                for f in frases(p):
                    m = RE_DEFINICAO.match(f)
                    if not m:
                        continue
                    termo = m["termo"].strip()
                    palavras = termo.lower().split()
                    if len(palavras) > 5 or palavras[0] in PRONOMES or termo.lower() in titulo.lower():
                        continue
                    verbo = "são" if m["verbo"] == "são" else "é"
                    pares.append({"pergunta": f"O que {verbo} {termo[0].lower() + termo[1:]}?",
                                  "resposta": f, "fonte": fonte, "origem": "definicao"})
            # 3) Regras e obrigações da seção (só quando o título não é uma pergunta,
            #    porque nesse caso a resposta do título já cobre as regras)
            regras = [f for p in paragrafos for f in frases(p) if RE_REGRA.search(f)]
            if regras and titulo != "Introdução" and not titulo.endswith("?"):
                pares.append({"pergunta": f"Quais são as regras sobre {titulo[0].lower() + titulo[1:]}?",
                              "resposta": cortar(" ".join(regras)), "fonte": fonte, "origem": "regra"})
    # remove perguntas repetidas
    unicos, vistos = [], set()
    for par in pares:
        if par["pergunta"].lower() not in vistos:
            vistos.add(par["pergunta"].lower())
            unicos.append(par)
    return unicos


def gerar_conversas(pares: list[dict]) -> list[dict]:
    conversas = []
    for par in pares:
        conversas.append({"messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": par["pergunta"]},
            {"role": "assistant", "content": f"{par['resposta']}\n\nFonte: {Path(par['fonte']).name}"},
        ]})
    return conversas


def salvar(registros: list[dict], pasta: Path, nome: str, semente: int = 42) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    embaralhados = registros[:]
    random.Random(semente).shuffle(embaralhados)
    n_val = max(1, len(embaralhados) // 10) if len(embaralhados) >= 10 else 0
    partes = {"": registros, "_treino": embaralhados[n_val:], "_validacao": embaralhados[:n_val]}
    for sufixo, dados in partes.items():
        with open(pasta / f"{nome}{sufixo}.jsonl", "w", encoding="utf-8") as f:
            for r in dados:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"total": len(registros), "treino": len(partes["_treino"]), "validacao": len(partes["_validacao"])}


# ---------------------------------------------------------------------------


def main(entrada: Path = ENTRADA_PADRAO, saida: Path = SAIDA_PADRAO) -> dict:
    arquivos = sorted(p for p in entrada.glob("**/*") if p.suffix.lower() in FORMATOS)
    if not arquivos:
        sys.exit(f"Nenhum documento em {entrada}. Formatos aceitos: {', '.join(sorted(FORMATOS))}")

    est = Estatisticas()
    vistos: set[str] = set()
    docs, por_arquivo = [], {}
    for arq in arquivos:
        try:
            paginas = [normalizar(p) for p in extrair_paginas(arq)]
        except Exception as erro:  # noqa: BLE001 - um arquivo ruim não derruba o lote
            print(f"[aviso] não consegui ler {arq.name}: {erro}")
            continue
        linhas = [l for pag in remover_repetidas(paginas, est) for l in pag + [""]]
        secoes = limpar_paragrafos(montar_secoes(linhas, est), est, vistos)
        fonte = str(arq.relative_to(entrada))
        docs.append((fonte, secoes))
        por_arquivo[fonte] = {"paginas": len(paginas), "secoes": len(secoes),
                              "paragrafos": sum(len(p) for _, p in secoes)}
        print(f"{fonte}: {len(paginas)} página(s), {len(secoes)} seções")

    texto = gerar_texto_puro(docs)
    pares = gerar_perguntas(docs)
    conversas = gerar_conversas(pares)

    relatorio = {
        "documentos": por_arquivo,
        "limpeza": {
            "linhas_brutas": est.linhas_brutas,
            "cabecalhos_rodapes_removidos": est.cabecalhos_rodapes,
            "numeros_de_pagina_removidos": est.numeros_pagina,
            "hifenizacoes_corrigidas": est.hifenizacoes,
            "paragrafos_duplicados_removidos": est.duplicados,
            "trechos_curtos_removidos": est.curtos,
            "dados_pessoais_mascarados": dict(est.dados_mascarados),
        },
        "corpus": {
            "texto_puro": salvar(texto, saida, "texto_puro"),
            "perguntas_respostas": salvar(pares, saida, "perguntas_respostas"),
            "conversacional": salvar(conversas, saida, "conversacional"),
        },
        "origem_das_perguntas": dict(Counter(p["origem"] for p in pares)),
    }
    (saida / "relatorio.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(relatorio["corpus"], ensure_ascii=False))
    return relatorio


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:3]]
    main(*args)
