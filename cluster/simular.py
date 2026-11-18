"""Gera os modelos do iSPD, roda as simulações pelo modo terminal e calcula speedup e eficiência.

Cenário: 1000 fotos chegam juntas e precisam ser classificadas por um cluster.
Cada tarefa = 1 foto: 200 a 400 Mflop de processamento e 16 a 32 Mbits de transferência.

Uso (precisa do Java e do iSPD.jar, baixado de https://www.dcce.ibilce.unesp.br/spd/downloads.php):
    python cluster/simular.py --ispd C:/caminho/iSPD.jar

Cada cenário roda N_SIMULACOES vezes (a carga é aleatória) e o iSPD devolve a média.
Os modelos ficam em cluster/modelos/ e podem ser abertos na interface gráfica do iSPD.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

PASTA = Path(__file__).resolve().parent
MODELOS = PASTA / "modelos"
PADRAO_ISPD = PASTA.parent.parent / "iSPD" / "iSPD.jar"
N_SIMULACOES = 10

# grupo, nome, descrição, escalonador, banda (Mbps), lista de clusters [(nós, Mflop/s)]
# Grupos A e B: 1 cluster ligado ao mestre por 1 link (escalabilidade e escalonador).
# Grupos C e D: 2 clusters de 4 nós, cada um com seu link (nós iguais x nós desiguais).
# Só se comparam cenários do mesmo grupo, que têm a mesma rede.
CENARIOS = [
    ("A", "C1", "1 cluster, 2 nós", "RoundRobin", 1000, [(2, 10000)]),
    ("A", "C2", "1 cluster, 4 nós", "RoundRobin", 1000, [(4, 10000)]),
    ("A", "C3", "1 cluster, 8 nós", "RoundRobin", 1000, [(8, 10000)]),
    ("A", "C4", "1 cluster, 8 nós", "Workqueue", 1000, [(8, 10000)]),
    ("B", "C5", "1 cluster, 2 nós", "RoundRobin", 10000, [(2, 10000)]),
    ("B", "C6", "1 cluster, 4 nós", "RoundRobin", 10000, [(4, 10000)]),
    ("B", "C7", "1 cluster, 8 nós", "RoundRobin", 10000, [(8, 10000)]),
    ("B", "C8", "1 cluster, 8 nós", "Workqueue", 10000, [(8, 10000)]),
    ("C", "C9", "2 clusters iguais (4+4 rápidos)", "RoundRobin", 1000, [(4, 10000), (4, 10000)]),
    ("C", "C10", "2 clusters desiguais (4 rápidos + 4 lentos)", "RoundRobin", 1000, [(4, 10000), (4, 5000)]),
    ("C", "C11", "2 clusters desiguais (4 rápidos + 4 lentos)", "Workqueue", 1000, [(4, 10000), (4, 5000)]),
    ("D", "C12", "2 clusters iguais (4+4 rápidos)", "RoundRobin", 10000, [(4, 10000), (4, 10000)]),
    ("D", "C13", "2 clusters desiguais (4 rápidos + 4 lentos)", "RoundRobin", 10000, [(4, 10000), (4, 5000)]),
    ("D", "C14", "2 clusters desiguais (4 rápidos + 4 lentos)", "Workqueue", 10000, [(4, 10000), (4, 5000)]),
]


def caracteristica(poder: float) -> str:
    return (f'        <characteristic>\n'
            f'            <process number="1" power="{poder:.1f}"/>\n'
            f'            <memory size="0.0"/>\n'
            f'            <hard_disk size="0.0"/>\n'
            f'        </characteristic>\n')


def gerar_modelo(escalonador: str, banda: float, clusters: list[tuple[int, float]]) -> str:
    """Monta o XML (.imsx) no mesmo formato que a interface do iSPD salva."""
    ids_clusters = list(range(1, len(clusters) + 1))
    escravos = "".join(f'            <slave id="{i}"/>\n' for i in ids_clusters)
    xml = ('<?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>\n'
           '<!DOCTYPE system SYSTEM "iSPD.dtd">\n<system version="1.2">\n    <owner id="user1"/>\n'
           '    <machine id="mestre" load="0.0" owner="user1" power="10000.0">\n'
           f'        <master scheduler="{escalonador}">\n{escravos}        </master>\n'
           '        <position x="420" y="150"/>\n        <icon_id global="0" local="0"/>\n'
           + caracteristica(10000) + '    </machine>\n')
    for i, (nos, poder) in zip(ids_clusters, clusters):
        xml += (f'    <cluster bandwidth="{banda:.1f}" id="cluster{i}" latency="0.001" master="false" '
                f'nodes="{nos}" owner="user1" power="{poder:.1f}" scheduler="---">\n'
                f'        <position x="195" y="{100 * i}"/>\n        <icon_id global="{i}" local="{i}"/>\n'
                + caracteristica(poder) + '    </cluster>\n')
    proximo = len(clusters) + 1
    for k, i in enumerate(ids_clusters):
        for origem, destino in ((0, i), (i, 0)):
            gid = proximo + 2 * k + (origem != 0)
            xml += (f'    <link bandwidth="{banda:.1f}" id="link{gid}" latency="0.001" load="0.0">\n'
                    f'        <connect destination="{destino}" origination="{origem}"/>\n'
                    f'        <position x="420" y="150"/>\n        <position x="195" y="{100 * i}"/>\n'
                    f'        <icon_id global="{gid}" local="{gid - proximo}"/>\n    </link>\n')
    xml += ('    <load>\n        <random tasks="1000" time_arrival="0">\n'
            '            <size average="300" maximum="400" minimum="200" probability="50.0" type="computing"/>\n'
            '            <size average="24" maximum="32" minimum="16" probability="50.0" type="communication"/>\n'
            '        </random>\n    </load>\n</system>\n')
    return xml


def simular(ispd: Path, modelo: Path) -> dict:
    saida = subprocess.run(["java", "-jar", str(ispd), "-n", str(N_SIMULACOES), str(modelo)],
                           capture_output=True, text=True, cwd=ispd.parent, timeout=600).stdout

    def valor(rotulo):
        m = re.search(rf"{rotulo}\s*=\s*([\d.]+)", saida)
        if not m:
            raise RuntimeError(f"Não achei '{rotulo}' na saída do iSPD:\n{saida}")
        return float(m.group(1))

    return {"tempo_total_s": valor("Total Simulated Time"),
            "ociosidade_processamento_pct": valor("Idleness of processing resources"),
            "ociosidade_comunicacao_pct": valor("Idleness of communication resources")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ispd", type=Path, default=PADRAO_ISPD)
    args = parser.parse_args()
    MODELOS.mkdir(exist_ok=True)

    linhas = []
    for grupo, nome, descricao, escalonador, banda, clusters in CENARIOS:
        modelo = MODELOS / f"{nome}.imsx"
        modelo.write_text(gerar_modelo(escalonador, banda, clusters), encoding="iso-8859-1")
        r = simular(args.ispd, modelo)
        nos = sum(n for n, _ in clusters)
        linhas.append({"grupo": grupo, "cenario": nome, "descricao": descricao, "nos": nos, "escalonador": escalonador,
                       "banda_mbps": banda, "nos_desiguais": "sim" if len({p for _, p in clusters}) > 1 else "nao", **r})
        print(f"{grupo} {nome:<4} {descricao:<45} {banda:>6} Mbps {escalonador:<10} {r['tempo_total_s']:>7.2f} s")

    # Grupos A e B: speedup e eficiência em relação ao cluster de 2 nós da mesma rede.
    # Grupos C e D: diferença de tempo em relação aos 2 clusters iguais da mesma rede.
    for l in linhas:
        ref = next(x for x in linhas if x["grupo"] == l["grupo"])  # 1º cenário do grupo
        if l["grupo"] in ("A", "B"):
            speedup = ref["tempo_total_s"] / l["tempo_total_s"]
            l["speedup_vs_2_nos"] = round(speedup, 3)
            l["eficiencia_pct"] = round(100 * speedup / (l["nos"] / ref["nos"]), 1)
            l["diferenca_vs_referencia_pct"] = ""
        else:
            l["speedup_vs_2_nos"] = l["eficiencia_pct"] = ""
            l["diferenca_vs_referencia_pct"] = round(100 * (l["tempo_total_s"] / ref["tempo_total_s"] - 1), 1)

    with open(PASTA / "resultados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
