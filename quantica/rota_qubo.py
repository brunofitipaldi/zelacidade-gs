"""Otimização da rota da equipe de manutenção (Computação Quântica & IA).

Problema: a equipe sai da base da subprefeitura, visita os chamados abertos e volta.
Qual a ordem de visita com menor distância? É o problema do caixeiro-viajante (TSP),
que cresce de forma fatorial e é um dos casos de uso estudados para computação quântica.

O script compara, na mesma instância:
1. Força bruta clássica (resposta exata, só funciona com poucos pontos).
2. Vizinho mais próximo (heurística clássica rápida, sem garantia de ótimo).
3. Formulação QUBO, que é o formato aceito por recozimento quântico (D-Wave) e pelo QAOA.
   - Para 4 chamados, o QUBO tem 16 variáveis binárias e dá para conferir todas as 2^16
     combinações: isso prova que a formulação está certa (o mínimo do QUBO é a rota ótima).
   - Recozimento simulado (simulated annealing) resolve o mesmo QUBO. Ele roda em
     computador clássico e serve de referência para o que um annealer quântico faria.

Nenhum hardware ou simulador quântico foi usado: o objetivo é mostrar a formulação, medir
o gargalo clássico e embasar o roadmap em quantica/README.md.

Uso:
    python quantica/rota_qubo.py
"""

from __future__ import annotations

import itertools
import json
import math
import time
from pathlib import Path

import numpy as np

PASTA = Path(__file__).resolve().parent
FATOR_PENALIDADE = 1.5

# Centro aproximado de cada bairro (coordenadas aproximadas, só para o exemplo).
BASE = ("Base – Subprefeitura Sé", -23.5505, -46.6340)
CHAMADOS = [
    ("Liberdade", -23.5587, -46.6350),
    ("Bela Vista", -23.5617, -46.6480),
    ("Consolação", -23.5550, -46.6600),
    ("República", -23.5440, -46.6420),
    ("Brás", -23.5440, -46.6160),
    ("Mooca", -23.5550, -46.5990),
    ("Vila Mariana", -23.5890, -46.6350),
    ("Pinheiros", -23.5670, -46.6930),
]


def distancia_km(a, b) -> float:
    """Distância em linha reta (fórmula de Haversine)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[1], a[2], b[1], b[2]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def matriz(pontos) -> np.ndarray:
    n = len(pontos)
    return np.array([[distancia_km(pontos[i], pontos[j]) for j in range(n)] for i in range(n)])


def custo(rota, d) -> float:
    """rota = ordem dos chamados (índices 1..n); a base é o índice 0, no início e no fim."""
    caminho = [0, *rota, 0]
    return float(sum(d[caminho[k], caminho[k + 1]] for k in range(len(caminho) - 1)))


def forca_bruta(d):
    n = len(d) - 1
    melhor = min(itertools.permutations(range(1, n + 1)), key=lambda r: custo(r, d))
    return list(melhor), custo(melhor, d)


def vizinho_mais_proximo(d):
    faltam, atual, rota = set(range(1, len(d))), 0, []
    while faltam:
        atual = min(faltam, key=lambda j: d[atual, j])
        rota.append(atual)
        faltam.remove(atual)
    return rota, custo(rota, d)


# --- QUBO ------------------------------------------------------------------
# Variável x[i,t] = 1 se o chamado i é visitado na posição t. São n*n variáveis (qubits).
# Energia = distância da rota + A * (penalidades para cada chamado e cada posição usados 1 vez).

def montar_qubo(d, fator_penalidade: float = FATOR_PENALIDADE) -> tuple[np.ndarray, float]:
    n = len(d) - 1
    # A penalidade precisa ser maior que o ganho de quebrar uma restrição, mas se for grande
    # demais o "relevo" de energia fica íngreme e o recozimento trava em rotas ruins.
    A = float(d.max()) * fator_penalidade
    idx = lambda i, t: i * n + t  # noqa: E731
    Q = np.zeros((n * n, n * n))
    const = 0.0

    def soma_um(variaveis):
        # A * (1 - soma x)^2 = A * (1 - 2*soma x + soma x^2 + 2*soma_{a<b} xa xb), com x^2 = x
        nonlocal const
        const += A
        for a in variaveis:
            Q[a, a] -= A
        for a, b in itertools.combinations(variaveis, 2):
            Q[a, b] += 2 * A

    for i in range(n):
        soma_um([idx(i, t) for t in range(n)])
    for t in range(n):
        soma_um([idx(i, t) for i in range(n)])

    for i in range(n):  # saída da base e volta para a base
        Q[idx(i, 0), idx(i, 0)] += d[0, i + 1]
        Q[idx(i, n - 1), idx(i, n - 1)] += d[i + 1, 0]
    for t in range(n - 1):  # trechos entre chamados consecutivos
        for i in range(n):
            for j in range(n):
                if i != j:
                    a, b = sorted((idx(i, t), idx(j, t + 1)))
                    Q[a, b] += d[i + 1, j + 1]
    return Q, const


def energia(x, Q, const) -> float:
    return float(x @ Q @ x) + const


def decodificar(x, n):
    m = x.reshape(n, n)
    if not (m.sum(axis=0) == 1).all() or not (m.sum(axis=1) == 1).all():
        return None  # solução inválida (quebrou alguma restrição)
    return [int(np.argmax(m[:, t])) + 1 for t in range(n)]


def enumerar_qubo(Q, const):
    """Testa todas as 2^N combinações (só para N pequeno) e devolve a de menor energia."""
    N = len(Q)
    bits = ((np.arange(2 ** N)[:, None] >> np.arange(N)) & 1).astype(float)
    Qs = np.triu(Q)
    energias = np.einsum("ki,ij,kj->k", bits, Qs, bits) + const
    k = int(np.argmin(energias))
    return bits[k], float(energias[k])


def recozimento_simulado(Q, const, passos=20000, rodadas=20, semente=42):
    rng = np.random.default_rng(semente)
    N = len(Q)
    U = np.triu(Q)
    S = U + np.triu(Q, 1).T  # simétrica: S[i,j] = acoplamento entre i e j
    melhor_x, melhor_e = None, math.inf
    for _ in range(rodadas):
        x = rng.integers(0, 2, N).astype(float)
        e = energia(x, U, const)
        for k in range(passos):
            T = 50 * (0.01 / 50) ** (k / passos)  # temperatura cai de 50 até 0,01
            i = rng.integers(N)
            # variação de energia ao inverter o bit i
            delta = (1 - 2 * x[i]) * (S[i, i] + S[i] @ x - S[i, i] * x[i])
            if delta < 0 or rng.random() < math.exp(-delta / T):
                x[i] = 1 - x[i]
                e += delta
                if e < melhor_e - 1e-9:
                    melhor_x, melhor_e = x.copy(), e
    return melhor_x, energia(melhor_x, U, const)


def nomes(rota, pontos):
    return [pontos[0][0], *[pontos[i][0] for i in rota], pontos[0][0]]


def cronometrar(f, *args):
    t0 = time.perf_counter()
    r = f(*args)
    return r, round(time.perf_counter() - t0, 4)


def main():
    resultado = {"observacao": "Coordenadas aproximadas dos bairros e distância em linha reta. "
                               "Nenhum hardware quântico foi usado."}

    # 1) Instância de 8 chamados: clássico exato x heurística
    pontos = [BASE, *CHAMADOS]
    d = matriz(pontos)
    (rota_fb, km_fb), t_fb = cronometrar(forca_bruta, d)
    (rota_vp, km_vp), t_vp = cronometrar(vizinho_mais_proximo, d)
    resultado["classico_8_chamados"] = {
        "forca_bruta": {"km": round(km_fb, 2), "segundos": t_fb, "rota": nomes(rota_fb, pontos),
                        "rotas_testadas": math.factorial(len(CHAMADOS))},
        "vizinho_mais_proximo": {"km": round(km_vp, 2), "segundos": t_vp, "rota": nomes(rota_vp, pontos),
                                 "diferenca_para_otimo_pct": round(100 * (km_vp / km_fb - 1), 1)},
    }

    # 2) Instâncias pequenas em QUBO
    resultado["qubo"] = []
    for n in (4, 6, 8):
        pts = [BASE, *CHAMADOS[:n]]
        dn = matriz(pts)
        rota_ok, km_ok = forca_bruta(dn)
        Q, const = montar_qubo(dn)
        linha = {"chamados": n, "qubits": n * n, "otimo_classico_km": round(km_ok, 2)}
        if n * n <= 16:
            (x, e), t = cronometrar(enumerar_qubo, Q, const)
            rota_q = decodificar(x, n)
            linha["enumeracao_completa"] = {
                "combinacoes": 2 ** (n * n), "segundos": t, "energia": round(e, 2),
                "rota": nomes(rota_q, pts) if rota_q else None,
                "igual_ao_otimo": rota_q is not None and abs(custo(rota_q, dn) - km_ok) < 1e-9,
            }
        (x, e), t = cronometrar(recozimento_simulado, Q, const)
        rota_sa = decodificar(x, n)
        linha["recozimento_simulado"] = {
            "segundos": t, "valida": rota_sa is not None,
            "km": round(custo(rota_sa, dn), 2) if rota_sa else None,
            "rota": nomes(rota_sa, pts) if rota_sa else None,
            "igual_ao_otimo": rota_sa is not None and abs(custo(rota_sa, dn) - km_ok) < 1e-9,
        }
        resultado["qubo"].append(linha)

    # 3) Crescimento do problema (gargalo)
    resultado["crescimento"] = [
        {"chamados": n, "rotas_possiveis": f"{math.factorial(n):.3g}", "qubits_qubo": n * n}
        for n in (5, 8, 10, 15, 20, 30, 50)
    ]

    (PASTA / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
