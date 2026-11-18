# Guia do iSPD – Cluster Computing

> Guia usado para montar o primeiro cenário na interface gráfica. O experimento final (14 cenários,
> rodados pelo modo terminal com `simular.py`) e os resultados estão em `README.md`.

**Pergunta do experimento:** se o ZelaCidade receber as fotos da cidade inteira, quantas máquinas o
cluster precisa para classificar todas rápido, e qual política de escalonamento distribui melhor?

## 0. Instalar e abrir (5 min)

1. Baixe o `iSPD.jar` da página oficial do grupo da UNESP:
   https://www.dcce.ibilce.unesp.br/spd/downloads.php (3,1 MB).
2. Dê dois cliques no arquivo. Se não abrir, no terminal da pasta onde ele está:
   `java -jar iSPD.jar`

## 1. Valores que vão em todos os cenários

**Carga de trabalho** (cada tarefa = classificar 1 foto enviada por um cidadão):

| Campo | Valor | Por quê |
| --- | --- | --- |
| Número de tarefas | 1000 | 1000 fotos chegando num pico |
| Tamanho computacional | 200 a 400 Mflop | Pré-processamento + MobileNetV3 + gravação |
| Tamanho de comunicação | 16 a 32 Mbits | Uma foto de celular de 2 a 4 MB |
| Tipo / distribuição | Aleatória (random), uniforme | |

**Máquinas e rede:**

| Item | Valor |
| --- | --- |
| Poder computacional de cada nó | 10000 Mflop/s |
| Largura de banda dos links | 1000 Mbps (1 Gbps) |
| Latência dos links | 0,001 s |
| Mestre (master) | 1 máquina que só distribui as tarefas |

## 2. Os 6 cenários

Monte, simule e anote cada um. **Mude só o que a tabela manda**, o resto fica igual.

| Cenário | Nós escravos | Escalonador | O que muda | Para mostrar |
| --- | --- | --- | --- | --- |
| C1 | 2 | RoundRobin | – | Ponto de partida |
| C2 | 4 | RoundRobin | – | Escalabilidade |
| C3 | 8 | RoundRobin | – | Escalabilidade |
| C4 | 8 | Workqueue | Escalonador | Distribuição de tarefas |
| C5 | 8 (4 de 10000 + 4 de 5000 Mflop/s) | RoundRobin | Nós diferentes | Distribuição com máquinas desiguais |
| C6 | 8 (4 de 10000 + 4 de 5000 Mflop/s) | Workqueue | Nós diferentes + escalonador | Distribuição com máquinas desiguais |

**Opcional (se sobrar tempo):** C7 = C3 com banda de **100 Mbps** em vez de 1000, para mostrar a rede
virando gargalo.

## 3. Como montar um cenário

O jeito mais simples é usar o ícone de **Cluster**, que já representa vários nós iguais:

1. **Novo modelo** (File > New).
2. Coloque **1 Máquina** (será o mestre) e **1 Cluster** na área de desenho.
3. Ligue os dois com um **Link** (banda 1000 Mbps, latência 0,001).
4. Clique duas vezes na **Máquina** e configure:
   - marque como **Master**;
   - escolha o **escalonador** (RoundRobin ou Workqueue);
   - na lista de escravos, marque o cluster.
5. Clique duas vezes no **Cluster**: número de escravos (2, 4 ou 8) e poder computacional
   (10000 Mflop/s); banda interna 1000 Mbps e latência 0,001.
6. Abra a **carga de trabalho** (Workload / botão de tarefas) e preencha com os valores da seção 1.
7. **Salve o modelo** com o nome do cenário (`C1.ims`, `C2.ims`...) dentro de `zelacidade-gs/cluster/`.
8. Clique em **Simular**.

Para **C5 e C6** (nós diferentes): em vez de 1 cluster, use **2 clusters** de 4 escravos ligados ao
mestre, um com 10000 e outro com 5000 Mflop/s.

Para mudar só o escalonador (C3 → C4, C5 → C6), abra o modelo, troque na Máquina mestre e use
**Salvar como**.

## 4. O que anotar de cada simulação

Na janela de resultados, procure e anote em `cluster/resultados.csv`:

- **Tempo total simulado** (makespan / *simulation time*), em segundos;
- **Utilização média** dos escravos (%), se aparecer;
- e tire **1 print** da janela de resultados (`C1_resultado.png`, `C2_resultado.png`...).

Também tire **1 print do desenho do modelo** de pelo menos um cenário (ex.: `C3_modelo.png`) e de C5.

## 5. Quando terminar

Me avise. Com os tempos anotados eu calculo o **speedup** (quanto mais rápido ficou em relação ao C1)
e a **eficiência** (speedup dividido pelo número de nós), monto os gráficos e o `cluster/README.md`.

Se alguma tela estiver diferente do que está aqui (os nomes mudam um pouco entre versões), me manda um
print que eu te digo onde clicar.
