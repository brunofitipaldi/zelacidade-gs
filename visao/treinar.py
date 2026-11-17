"""Treino e avaliação do classificador de danos urbanos (Visão Computacional).

Dataset: "Multiclass Road Surface Damage Classification Dataset: Computer Vision" (Mendeley Data,
doi 10.17632/697w4jkr2x.2), 3 classes: Pothole, Crack e Surface Erosion.
Baixar e extrair em data/visao_dataset/Dataset/<classe>/*.jpg (a pasta não vai para o Git).

Arquitetura: MobileNetV3-Small pré-treinada no ImageNet como extratora de características
(congelada) + uma camada linear treinada aqui. Escolhida por ser pequena (~2,5 M parâmetros) e
rápida em CPU/celular, o que permite classificar a foto no momento do envio.

Etapas:
1. Limpeza: remove fotos duplicadas (mesmo conteúdo em bytes). Se a mesma foto aparece em
   classes diferentes, todas as cópias são descartadas, porque o rótulo é contraditório.
2. Extração de características de todas as fotos (cache em visao/cache/).
3. Agrupamento de fotos quase iguais (mesma cena redimensionada ou recortada: similaridade de
   cosseno >= 0,97 entre as características). Cada grupo vai inteiro para um só lado da divisão,
   para a mesma cena não aparecer no treino e no teste.
4. Divisão estratificada por grupos: ~70% treino / 15% validação / 15% teste, semente 42.
5. Treino da camada final e avaliação no teste: acurácia, precisão, revocação, F1, matriz de confusão e tempo por foto.

Uso:
    python visao/treinar.py
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import models

RAIZ = Path(__file__).resolve().parent.parent
PASTA = Path(__file__).resolve().parent
DATASET = RAIZ / "data" / "visao_dataset" / "Dataset"
CACHE = PASTA / "cache"

# Pasta do dataset -> tipo usado no ZelaCidade
CLASSES = {"Pothole": "buraco", "Crack": "rachadura", "Surface Erosion": "desgaste_asfalto"}
SEMENTE = 42
LIMIAR_QUASE_IGUAL = 0.97


def preparar_entrada():
    pesos = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
    return pesos, pesos.transforms()


def carregar_extrator():
    pesos, transformar = preparar_entrada()
    rede = models.mobilenet_v3_small(weights=pesos)
    rede.classifier = torch.nn.Identity()  # saída: vetor de 576 características
    rede.eval()
    return rede, transformar


def listar_imagens():
    """Lê o dataset e remove duplicatas. Devolve [(caminho, classe)] e um resumo da limpeza."""
    por_hash = defaultdict(list)
    for pasta, tipo in CLASSES.items():
        for arq in sorted((DATASET / pasta).iterdir()):
            if arq.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                por_hash[hashlib.md5(arq.read_bytes()).hexdigest()].append((arq, tipo))

    itens, conflitos, repetidas = [], 0, 0
    for copias in por_hash.values():
        tipos = {t for _, t in copias}
        if len(tipos) > 1:
            conflitos += 1
            continue
        repetidas += len(copias) - 1
        itens.append(copias[0])
    total = sum(len(v) for v in por_hash.values())
    resumo = {"imagens_no_dataset": total, "copias_repetidas_removidas": repetidas,
              "fotos_com_rotulo_contraditorio_removidas": conflitos,
              "imagens_usadas": len(itens)}
    return itens, resumo


def agrupar_quase_iguais(X, y):
    """Une fotos com características quase idênticas (union-find). Devolve o grupo de cada foto."""
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)
    pai = list(range(len(X)))

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    sim = Xn @ Xn.T
    for i, j in zip(*np.where(np.triu(sim, 1) >= LIMIAR_QUASE_IGUAL)):
        pai[raiz(i)] = raiz(j)
    return np.array([raiz(i) for i in range(len(X))])


def dividir(grupos, y):
    """Divide os grupos (não as fotos) em treino/validação/teste, estratificado pela classe."""
    rng = random.Random(SEMENTE)
    idx = {"treino": [], "validacao": [], "teste": []}
    descartados = 0
    por_classe = defaultdict(list)
    for g in np.unique(grupos):
        membros = np.where(grupos == g)[0]
        classes = set(y[membros])
        if len(classes) > 1:  # cena parecida com rótulos diferentes: fica fora
            descartados += len(membros)
            continue
        por_classe[classes.pop()].append(list(membros))
    for lista in por_classe.values():
        rng.shuffle(lista)
        total = sum(len(m) for m in lista)
        acumulado = 0
        for membros in lista:
            if acumulado < 0.15 * total:
                idx["teste"] += membros
            elif acumulado < 0.30 * total:
                idx["validacao"] += membros
            else:
                idx["treino"] += membros
            acumulado += len(membros)
    return {k: np.array(sorted(v)) for k, v in idx.items()}, descartados


@torch.no_grad()
def extrair(rede, transformar, itens, nome):
    CACHE.mkdir(exist_ok=True)
    arquivo = CACHE / f"{nome}.npz"
    caminhos = [str(p.relative_to(DATASET)) for p, _ in itens]
    if arquivo.exists():
        dados = np.load(arquivo, allow_pickle=False)
        if list(dados["caminhos"]) == caminhos:
            return dados["X"], dados["y"]
    tipos = list(CLASSES.values())
    X, y = [], []
    for k in range(0, len(itens), 32):
        lote = itens[k:k + 32]
        imgs = torch.stack([transformar(Image.open(p).convert("RGB")) for p, _ in lote])
        X.append(rede(imgs).numpy())
        y += [tipos.index(t) for _, t in lote]
    X, y = np.concatenate(X), np.array(y)
    np.savez(arquivo, X=X, y=y, caminhos=np.array(caminhos))
    return X, y


def treinar_cabeca(Xtr, ytr, Xva, yva, epocas=300):
    torch.manual_seed(SEMENTE)
    media, desvio = Xtr.mean(0), Xtr.std(0) + 1e-6
    norm = lambda X: torch.tensor((X - media) / desvio, dtype=torch.float32)  # noqa: E731
    xtr, xva = norm(Xtr), norm(Xva)
    ttr, tva = torch.tensor(ytr), torch.tensor(yva)
    # Peso por classe: a classe com menos fotos pesa mais na perda.
    contagem = np.bincount(ytr, minlength=len(CLASSES))
    peso = torch.tensor(len(ytr) / (len(CLASSES) * contagem), dtype=torch.float32)

    melhor = (0.0, None, 0)
    for wd in (1e-4, 1e-3, 1e-2):  # escolhe a regularização pela validação
        cabeca = torch.nn.Linear(Xtr.shape[1], len(CLASSES))
        otim = torch.optim.Adam(cabeca.parameters(), lr=1e-3, weight_decay=wd)
        perda = torch.nn.CrossEntropyLoss(weight=peso)
        for _ in range(epocas):
            otim.zero_grad()
            perda(cabeca(xtr), ttr).backward()
            otim.step()
        with torch.no_grad():
            acc = (cabeca(xva).argmax(1) == tva).float().mean().item()
        if acc > melhor[0]:
            melhor = (acc, cabeca, wd)
    acc_val, cabeca, wd = melhor
    return cabeca, media, desvio, {"acuracia_validacao": round(acc_val, 4), "weight_decay": wd}


def metricas(y, pred):
    tipos = list(CLASSES.values())
    n = len(tipos)
    m = np.zeros((n, n), dtype=int)
    for a, b in zip(y, pred):
        m[a, b] += 1
    por_classe = {}
    for i, t in enumerate(tipos):
        vp = m[i, i]
        prec = vp / m[:, i].sum() if m[:, i].sum() else 0.0
        rev = vp / m[i].sum() if m[i].sum() else 0.0
        f1 = 2 * prec * rev / (prec + rev) if prec + rev else 0.0
        por_classe[t] = {"precisao": round(float(prec), 3), "revocacao": round(float(rev), 3),
                         "f1": round(float(f1), 3), "fotos_no_teste": int(m[i].sum())}
    return {"acuracia": round(float(np.trace(m) / m.sum()), 4), "por_classe": por_classe,
            "matriz_confusao": {"linhas_real_colunas_previsto": tipos, "valores": m.tolist()}}


def main():
    itens, limpeza = listar_imagens()
    rede, transformar = carregar_extrator()
    X, y = extrair(rede, transformar, itens, "todas")
    grupos = agrupar_quase_iguais(X, y)
    idx, descartados = dividir(grupos, y)
    limpeza["grupos_de_fotos_quase_iguais"] = int(sum(np.bincount(grupos) > 1))
    limpeza["fotos_quase_iguais_com_rotulos_diferentes_removidas"] = int(descartados)
    partes = {k: [itens[i] for i in v] for k, v in idx.items()}
    dados = {k: (X[v], y[v]) for k, v in idx.items()}

    cabeca, media, desvio, info = treinar_cabeca(*dados["treino"], *dados["validacao"])
    torch.save({"pesos": cabeca.state_dict(), "media": torch.tensor(media), "desvio": torch.tensor(desvio),
                "classes": list(CLASSES.values())}, PASTA / "modelo_cabeca.pt")

    Xte, yte = dados["teste"]
    with torch.no_grad():
        logits = cabeca(torch.tensor((Xte - media) / desvio, dtype=torch.float32))
        prob = torch.softmax(logits, 1).numpy()
    pred = prob.argmax(1)
    resultado = metricas(yte, pred)

    # Quantas fotos de teste ficariam abaixo do limiar de confiança (iriam para revisão humana)
    conf = prob.max(1)
    abaixo = conf < 0.60
    resultado["limiar_revisao_humana"] = {
        "limiar": 0.60, "fotos_para_revisao": int(abaixo.sum()),
        "acuracia_nas_fotos_acima_do_limiar": round(float((pred[~abaixo] == yte[~abaixo]).mean()), 4),
        "acuracia_nas_fotos_abaixo_do_limiar": round(float((pred[abaixo] == yte[abaixo]).mean()), 4)
        if abaixo.any() else None,
    }

    # Tempo de ponta a ponta (abrir foto + rede + camada final), em CPU, com 20 fotos de teste
    tempos = []
    with torch.no_grad():
        for p, _ in partes["teste"][:20]:
            t0 = time.perf_counter()
            x = transformar(Image.open(p).convert("RGB")).unsqueeze(0)
            cabeca(torch.tensor((rede(x).numpy() - media) / desvio, dtype=torch.float32))
            tempos.append((time.perf_counter() - t0) * 1000)
    resultado["tempo_por_foto_ms_cpu"] = round(float(np.median(tempos)), 1)

    saida = {"dataset": "Multiclass Road Surface Damage Classification Dataset (Mendeley Data, "
                        "doi 10.17632/697w4jkr2x.2)",
             "modelo": "MobileNetV3-Small (ImageNet, congelada) + camada linear",
             "limpeza": limpeza,
             "divisao": {k: len(v) for k, v in partes.items()},
             "treino": info, "teste": resultado}
    (PASTA / "metricas.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
