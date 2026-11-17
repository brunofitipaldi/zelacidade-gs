"""Avaliação do assistente com os casos de genai/casos_teste.json.

Métricas:
- acerto_busca@1 / @3: o documento certo aparece em 1º lugar / entre os 3 primeiros
- cobertura_palavras: a resposta contém os termos esperados
- recusa_correta: perguntas fora do escopo que o assistente recusou
- respostas_sem_base: perguntas fora do escopo que ele respondeu (risco de alucinação)
- recusa_indevida: perguntas do escopo que ele recusou

Uso:
    python genai/avaliar.py            # modo extrativo (sem custo)
    python genai/avaliar.py --claude   # usa o Claude (precisa de ANTHROPIC_API_KEY, gera custo)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assistente import Assistente  # noqa: E402

PASTA = Path(__file__).resolve().parent


def main(usar_claude: bool = False) -> dict:
    casos = json.loads((PASTA / "casos_teste.json").read_text(encoding="utf-8"))["casos"]
    assistente = Assistente(usar_claude=usar_claude)
    linhas, dentro, fora = [], [], []

    for c in casos:
        r = assistente.perguntar(c["pergunta"])
        if c.get("fora_do_escopo"):
            ok = not r["encontrou"]
            fora.append(ok)
            linhas.append({"pergunta": c["pergunta"], "tipo": "fora do escopo",
                           "resultado": "recusou" if ok else "RESPONDEU SEM BASE",
                           "score": r["score"], "resposta": r["resposta"]})
            continue
        top1 = bool(r["fontes"]) and c["fonte"] in r["fontes"][0]
        top3 = any(c["fonte"] in f for f in r["fontes"])
        palavras = all(p.lower() in r["resposta"].lower() for p in c["palavras"])
        dentro.append({"top1": top1, "top3": top3, "palavras": palavras, "recusou": not r["encontrou"]})
        linhas.append({"pergunta": c["pergunta"], "tipo": "no escopo",
                       "resultado": ("ok" if top1 and palavras else "parcial" if top3 else "errou")
                                    + (" (recusou)" if not r["encontrou"] else ""),
                       "score": r["score"], "fonte_encontrada": r["fontes"][0] if r["fontes"] else None,
                       "resposta": r["resposta"]})

    n_in, n_out = len(dentro), len(fora)
    metricas = {
        "modo": "claude" if assistente.usar_claude else "extrativo",
        "perguntas_no_escopo": n_in,
        "perguntas_fora_do_escopo": n_out,
        "acerto_busca@1": round(sum(d["top1"] for d in dentro) / n_in, 3),
        "acerto_busca@3": round(sum(d["top3"] for d in dentro) / n_in, 3),
        "cobertura_palavras": round(sum(d["palavras"] for d in dentro) / n_in, 3),
        "recusa_indevida": round(sum(d["recusou"] for d in dentro) / n_in, 3),
        "recusa_correta": round(sum(fora) / n_out, 3),
        "respostas_sem_base": round(1 - sum(fora) / n_out, 3),
    }

    saida = {"metricas": metricas, "casos": linhas}
    (PASTA / f"resultado_avaliacao_{metricas['modo']}.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    for l in linhas:
        print(f"[{l['resultado']:<22}] score {l['score']:>5}  {l['pergunta']}")
    print("\n" + json.dumps(metricas, ensure_ascii=False, indent=2))
    return saida


if __name__ == "__main__":
    main(usar_claude="--claude" in sys.argv)
