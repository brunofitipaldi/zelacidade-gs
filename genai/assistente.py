"""Assistente do ZelaCidade (Generative AI).

Responde dúvidas do cidadão usando só os documentos tratados pelo módulo de PLN
(pln/corpus/texto_puro.jsonl). Funciona em duas etapas:

1. Busca: um índice BM25 encontra os trechos mais parecidos com a pergunta.
   Se nenhum trecho for parecido o bastante, o assistente diz que não sabe
   em vez de inventar uma resposta.
2. Resposta:
   - modo "claude": se houver credencial da API da Anthropic (ANTHROPIC_API_KEY),
     o Claude redige a resposta usando apenas os trechos encontrados;
   - modo "extrativo" (padrão, sem custo): devolve as frases mais relevantes
     do melhor trecho, sem gerar texto novo.

Uso:
    python genai/assistente.py "Como peço o conserto de um buraco?"
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CORPUS = RAIZ / "pln" / "corpus" / "texto_puro.jsonl"

MODELO_CLAUDE = "claude-opus-5-5"
LIMIAR_SCORE = 4.0        # abaixo disso o assistente se recusa a responder
MIN_TERMOS_EM_COMUM = 2   # termos da pergunta que precisam aparecer no trecho

RESPOSTA_SEM_BASE = (
    "Não encontrei essa informação nos documentos que eu conheço. "
    "Para outros serviços da prefeitura, use o SP156 (telefone 156, site ou aplicativo)."
)

STOPWORDS = set("""
a o as os um uma uns umas de do da dos das no na nos nas em e ou que se por para pra com sem
ao aos à às é ser são foi era como qual quais quando onde quem eu meu minha meus minhas
voce você vc seu sua me mim nao não sim mais menos muito pouco ja já tem ter há isso isto
esse essa este esta pode posso devo deve preciso precisa fazer faço sobre entre até
""".split())


def normalizar_termo(palavra: str) -> str:
    palavra = unicodedata.normalize("NFD", palavra.lower())
    palavra = "".join(c for c in palavra if unicodedata.category(c) != "Mn")
    # radical simples: tira plural e algumas terminações comuns
    for sufixo in ("coes", "cao", "mente", "s"):
        if palavra.endswith(sufixo) and len(palavra) - len(sufixo) >= 4:
            palavra = palavra[: -len(sufixo)]
            break
    return palavra


def tokenizar(texto: str) -> list[str]:
    palavras = re.findall(r"[A-Za-zÀ-ú0-9]+(?:,[0-9]+)?", texto)
    return [normalizar_termo(p) for p in palavras if p.lower() not in STOPWORDS and len(p) > 1]


@dataclass
class Trecho:
    texto: str
    fonte: str
    titulo: str
    termos: Counter = field(default_factory=Counter)


class IndiceBM25:
    def __init__(self, trechos: list[Trecho], k1: float = 1.5, b: float = 0.75):
        self.trechos = trechos
        self.k1, self.b = k1, b
        self.media_tam = sum(sum(t.termos.values()) for t in trechos) / max(1, len(trechos))
        df = Counter(termo for t in trechos for termo in t.termos)
        n = len(trechos)
        self.idf = {termo: math.log(1 + (n - f + 0.5) / (f + 0.5)) for termo, f in df.items()}

    def buscar(self, pergunta: str, k: int = 3) -> list[tuple[float, int, Trecho]]:
        consulta = set(tokenizar(pergunta))
        resultados = []
        for t in self.trechos:
            tam = sum(t.termos.values())
            score, em_comum = 0.0, 0
            for termo in consulta:
                f = t.termos.get(termo, 0)
                if not f:
                    continue
                em_comum += 1
                score += self.idf[termo] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * tam / self.media_tam))
            if score > 0:
                resultados.append((score, em_comum, t))
        resultados.sort(key=lambda r: r[0], reverse=True)
        return resultados[:k]


def carregar_indice(caminho: Path = CORPUS) -> IndiceBM25:
    trechos = []
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            r = json.loads(linha)
            titulo = r["text"].split("\n", 1)[0]
            termos = Counter(tokenizar(r["text"]))
            termos.update(tokenizar(titulo))  # o título conta em dobro
            trechos.append(Trecho(r["text"], r["fonte"], titulo, termos))
    return IndiceBM25(trechos)


def frases_relevantes(pergunta: str, texto: str, maximo: int = 3) -> str:
    corpo = (texto.split("\n", 1)[1] if "\n" in texto else texto).strip()
    corpo = re.sub(r"\s*\n+\s*", " ", corpo)
    if len(corpo) <= 450:  # seção curta: devolve inteira para não cortar a informação
        return corpo
    frases = [f.strip() for f in re.split(r"(?<=[.!?;])\s+", corpo) if len(f.strip()) > 15]
    consulta = set(tokenizar(pergunta))
    notas = [(len(consulta & set(tokenizar(f))), i, f) for i, f in enumerate(frases)]
    # a primeira frase costuma introduzir o assunto (ou a lista que vem depois)
    escolhidas = {0} | {i for _, i, _ in sorted([n for n in notas if n[0] > 0], reverse=True)[: maximo - 1]}
    return " ".join(frases[i] for i in sorted(escolhidas))


def responder_com_claude(pergunta: str, trechos: list[Trecho]) -> str:
    import anthropic

    contexto = "\n\n".join(
        f"<trecho fonte=\"{t.fonte}\">\n{t.texto}\n</trecho>" for t in trechos
    )
    client = anthropic.Anthropic()
    resposta = client.beta.messages.create(
        model=MODELO_CLAUDE,
        max_tokens=4096,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=(
            "Você é o assistente do ZelaCidade e ajuda cidadãos com dúvidas sobre calçadas, "
            "buracos e serviços de zeladoria da Prefeitura de São Paulo. Responda em português, "
            "em até 4 frases, usando somente as informações dos trechos fornecidos. "
            "Se os trechos não respondem à pergunta, diga que não encontrou a informação e "
            "indique o SP156. Termine com 'Fonte:' e o nome do arquivo usado."
        ),
        messages=[{"role": "user", "content": f"{contexto}\n\nPergunta: {pergunta}"}],
    )
    if resposta.stop_reason == "refusal":
        return RESPOSTA_SEM_BASE
    return "".join(b.text for b in resposta.content if b.type == "text").strip()


def credencial_disponivel() -> bool:
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


class Assistente:
    def __init__(self, usar_claude: bool | None = None):
        self.indice = carregar_indice()
        self.usar_claude = credencial_disponivel() if usar_claude is None else usar_claude

    def perguntar(self, pergunta: str) -> dict:
        achados = self.indice.buscar(pergunta, k=3)
        melhor_score = achados[0][0] if achados else 0.0
        em_comum = achados[0][1] if achados else 0
        n_termos = len(set(tokenizar(pergunta)))
        minimo = min(MIN_TERMOS_EM_COMUM, n_termos)

        base = {
            "pergunta": pergunta,
            "score": round(melhor_score, 2),
            "fontes": [t.fonte for _, _, t in achados],
            "titulos": [t.titulo for _, _, t in achados],
        }
        if not achados or melhor_score < LIMIAR_SCORE or em_comum < minimo:
            return {**base, "encontrou": False, "modo": "recusa", "resposta": RESPOSTA_SEM_BASE}

        trechos = [t for s, _, t in achados if s >= LIMIAR_SCORE] or [achados[0][2]]
        if self.usar_claude:
            try:
                texto = responder_com_claude(pergunta, trechos)
                return {**base, "encontrou": True, "modo": "claude", "resposta": texto}
            except Exception as erro:  # noqa: BLE001 - sem rede ou sem crédito: cai no modo extrativo
                base["erro_claude"] = str(erro)
        melhor = trechos[0]
        texto = f"{frases_relevantes(pergunta, melhor.texto)}\n\nFonte: {melhor.fonte} (seção \"{melhor.titulo}\")"
        return {**base, "encontrou": True, "modo": "extrativo", "resposta": texto}


if __name__ == "__main__":
    pergunta = " ".join(sys.argv[1:]) or "Como peço o conserto de um buraco na rua?"
    r = Assistente().perguntar(pergunta)
    print(f"[{r['modo']}, score {r['score']}]\n{r['resposta']}")
