# Visão Computacional – classificação de danos urbanos

Classifica a foto enviada pelo cidadão em **buraco**, **rachadura** ou **desgaste do asfalto** e
sugere o tipo do chamado na aba "Reportar problema" do app.

```bash
python visao/treinar.py                       # limpa o dataset, treina e gera metricas.json
python visao/classificador.py caminho/foto.jpg
```

## Dados

**Multiclass Road Surface Damage Classification Dataset: Computer Vision** – Mendeley Data,
doi [10.17632/697w4jkr2x.2](https://data.mendeley.com/datasets/697w4jkr2x/2). Baixado em 17/11/2026
(arquivo de 260 MB, SHA-256 conferido). 1.530 fotos de pavimento em 3 classes: Pothole (401),
Crack (478) e Surface Erosion (651). As fotos ficam em `data/visao_dataset/` e **não vão para o Git**.

### Limpeza (feita pelo script)

| Problema encontrado | Fotos | O que foi feito |
| --- | --- | --- |
| Cópias idênticas da mesma foto | 186 | Mantida uma cópia |
| Mesma foto em duas classes diferentes (rótulo contraditório) | 44 | Todas as cópias descartadas |
| Fotos quase iguais (mesma cena redimensionada ou recortada) | 22 grupos | Cada grupo fica inteiro no treino **ou** no teste |
| Fotos quase iguais com rótulos diferentes | 17 | Descartadas |

Sem essa limpeza, a mesma cena caía no treino e no teste e a acurácia subia artificialmente
(85,6% antes de separar os grupos, 85,0% depois).

Divisão por grupos, estratificada pela classe, semente 42: **866 treino / 186 validação / 187 teste**.

## Arquitetura e justificativa

**MobileNetV3-Small** pré-treinada no ImageNet, usada **congelada** como extratora de características
(vetor de 576 números por foto), mais **uma camada linear** treinada com os dados limpos (pesos por
classe para compensar o desbalanceamento; regularização escolhida pela validação).

- **Tempo real:** a rede tem ~2,5 milhões de parâmetros e foi feita para celular. Em CPU, uma foto
  leva **cerca de 40 ms** de ponta a ponta, então o cidadão vê a sugestão na hora do envio.
- **Pouco dado:** com ~900 fotos de treino, treinar só a última camada evita sobreajuste e roda em
  segundos. O arquivo do modelo treinado (`modelo_cabeca.pt`) tem poucos KB.
- **Alternativas consideradas:** detecção de objetos (YOLO) daria a posição do dano, mas exige
  caixas desenhadas em cada foto, que esse dataset não tem; redes maiores (ResNet-50, ViT) seriam
  mais lentas sem garantia de ganho com tão poucas fotos.

## Resultados no conjunto de teste (187 fotos nunca vistas)

**Acurácia: 85,0%** · tempo mediano por foto: 41,5 ms (CPU)

| Classe | Precisão | Revocação | F1 | Fotos |
| --- | --- | --- | --- | --- |
| Buraco | 0,90 | 0,85 | 0,87 | 52 |
| Rachadura | 0,80 | 0,97 | 0,88 | 63 |
| Desgaste do asfalto | 0,87 | 0,75 | 0,81 | 72 |

Matriz de confusão (linha = classe real, coluna = previsto):

| Real ↓ / Previsto → | Buraco | Rachadura | Desgaste |
| --- | --- | --- | --- |
| **Buraco** | 44 | 2 | 6 |
| **Rachadura** | 0 | 61 | 2 |
| **Desgaste** | 5 | 13 | 54 |

Os valores exatos estão em `metricas.json`.

### Revisão humana

Quando a confiança fica abaixo de **60%**, o chamado entra em revisão humana (mesmo limiar do RPA).
No teste, 7 fotos ficaram abaixo do limiar, e o modelo **errou 5 delas** (acerto de 28,6%), enquanto
acertou 87,2% das demais. Ou seja, a confiança baixa de fato separa os casos duvidosos.

No app, o cidadão sempre pode trocar o tipo sugerido. Se trocar, o chamado é gravado sem a confiança
da IA, porque a decisão passou a ser dele.

## Limitações

- **Calçada quebrada não está no dataset.** Esse tipo continua sendo escolhido pelo cidadão.
- O modelo sempre escolhe uma das 3 classes, mesmo para fotos que não são de rua. Uma imagem
  sintética (elipse cinza) foi classificada como rachadura com 65%. Falta uma classe "não é problema
  urbano" ou um filtro de fotos fora do domínio.
- As fotos são de rodovias e ruas de outro país, a maioria em tons de cinza. O desempenho em fotos de
  São Paulo, tiradas de celular, ainda não foi medido.
- O erro mais comum é desgaste confundido com rachadura (13 fotos): as duas classes têm textura parecida
  e às vezes aparecem juntas.
- Classifica a foto inteira; não mostra onde está o dano nem mede o tamanho do buraco.
