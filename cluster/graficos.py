"""Gera os gráficos do experimento do iSPD a partir de cluster/resultados.csv.

Uso:
    python cluster/graficos.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

PASTA = Path(__file__).resolve().parent
AZUL, LARANJA = "#2a78d6", "#eb6834"  # paleta validada para daltonismo
TINTA, TINTA_SUAVE, GRADE = "#1f1f1e", "#6b6a63", "#e6e5e0"


def estilo(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRADE)
    ax.tick_params(colors=TINTA_SUAVE, labelsize=9)
    ax.grid(color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def escalabilidade(df):
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    estilo(ax)
    ax.grid(axis="x", visible=False)
    for grupo, cor, marcador, rotulo in (("A", LARANJA, "s", "Rede de 1 Gbps"),
                                         ("B", AZUL, "o", "Rede de 10 Gbps")):
        d = df[(df["grupo"] == grupo) & (df["escalonador"] == "RoundRobin")].sort_values("nos")
        ax.plot(d["nos"], d["tempo_total_s"], color=cor, linewidth=2, marker=marcador,
                markersize=8, markeredgecolor="white", markeredgewidth=1.5, label=rotulo)
        ultimo = d.iloc[-1]
        tempo = f"{ultimo['tempo_total_s']:.1f}".replace(".", ",")
        ax.annotate(f"{rotulo}\n{tempo} s", (ultimo["nos"], ultimo["tempo_total_s"]),
                    xytext=(10, 0), textcoords="offset points", va="center", fontsize=9, color=TINTA)
    ax.set_xticks([2, 4, 8])
    ax.set_xlim(1.5, 10.5)
    ax.set_ylim(0, 25)
    ax.set_xlabel("Nós no cluster", color=TINTA_SUAVE, fontsize=9)
    ax.set_ylabel("Tempo para classificar 1000 fotos (s)", color=TINTA_SUAVE, fontsize=9)
    ax.set_title("Mais nós só ajudam quando a rede acompanha", loc="left", fontsize=12, color=TINTA)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.text(0.01, 0.01, "Fonte: simulação no iSPD, média de 10 execuções, escalonador RoundRobin.",
             fontsize=7.5, color=TINTA_SUAVE)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(PASTA / "grafico_escalabilidade.png")
    plt.close(fig)


def heterogeneidade(df):
    fig, eixos = plt.subplots(1, 2, figsize=(9, 3.4), dpi=150, sharex=True)
    rotulos = {"C9": "4+4 iguais · RoundRobin", "C10": "4 rápidos + 4 lentos · RoundRobin",
               "C11": "4 rápidos + 4 lentos · Workqueue", "C12": "4+4 iguais · RoundRobin",
               "C13": "4 rápidos + 4 lentos · RoundRobin", "C14": "4 rápidos + 4 lentos · Workqueue"}
    for ax, grupo, titulo in zip(eixos, ("C", "D"), ("Rede de 1 Gbps", "Rede de 10 Gbps")):
        estilo(ax)
        ax.grid(axis="y", visible=False)
        d = df[df["grupo"] == grupo].iloc[::-1]
        y = range(len(d))
        ax.barh(list(y), d["tempo_total_s"], color=AZUL, height=0.55, edgecolor="white", linewidth=2)
        ax.set_yticks(list(y), [rotulos[c] for c in d["cenario"]], fontsize=8.5, color=TINTA)
        for yi, v in zip(y, d["tempo_total_s"]):
            ax.text(v + 0.2, yi, f"{v:.1f} s".replace(".", ","), va="center", fontsize=8.5, color=TINTA)
        ax.set_title(titulo, loc="left", fontsize=10, color=TINTA)
        ax.set_xlabel("Tempo (s)", color=TINTA_SUAVE, fontsize=9)
    eixos[0].set_xlim(0, 15)
    fig.suptitle("Com máquinas desiguais, o Workqueue só ajuda quando a rede não é o gargalo",
                 x=0.01, ha="left", fontsize=11.5, color=TINTA)
    fig.text(0.01, 0.01, "Fonte: simulação no iSPD, média de 10 execuções. 2 clusters de 4 nós, "
             "cada um com link próprio até o mestre.", fontsize=7.5, color=TINTA_SUAVE)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(PASTA / "grafico_heterogeneidade.png")
    plt.close(fig)


if __name__ == "__main__":
    dados = pd.read_csv(PASTA / "resultados.csv")
    escalabilidade(dados)
    heterogeneidade(dados)
    print("Gráficos salvos em", PASTA)
