"""Classifica a foto enviada pelo cidadão usando o modelo treinado em visao/treinar.py.

Uso:
    python visao/classificador.py caminho/da/foto.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from treinar import carregar_extrator  # noqa: E402

MODELO = Path(__file__).resolve().parent / "modelo_cabeca.pt"
LIMIAR_REVISAO = 0.60  # abaixo disso a foto vai para revisão humana (mesmo limiar do RPA)


class Classificador:
    def __init__(self, caminho: Path = MODELO):
        self.rede, self.transformar = carregar_extrator()
        ck = torch.load(caminho, weights_only=True)
        self.classes = ck["classes"]
        self.media, self.desvio = ck["media"], ck["desvio"]
        self.cabeca = torch.nn.Linear(self.media.shape[0], len(self.classes))
        self.cabeca.load_state_dict(ck["pesos"])
        self.cabeca.eval()

    @torch.no_grad()
    def classificar(self, imagem: Image.Image | str | Path) -> dict:
        if not isinstance(imagem, Image.Image):
            imagem = Image.open(imagem)
        x = self.transformar(imagem.convert("RGB")).unsqueeze(0)
        caracteristicas = (self.rede(x) - self.media) / self.desvio
        prob = torch.softmax(self.cabeca(caracteristicas.float()), 1)[0]
        k = int(prob.argmax())
        return {
            "tipo": self.classes[k],
            "confianca": round(float(prob[k]), 3),
            "probabilidades": {c: round(float(p), 3) for c, p in zip(self.classes, prob)},
            "revisao_humana": float(prob[k]) < LIMIAR_REVISAO,
        }


if __name__ == "__main__":
    print(Classificador().classificar(sys.argv[1]))
