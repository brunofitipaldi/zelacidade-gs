# Computação Quântica – rota das equipes de manutenção

## Gargalo escolhido: otimização

Cada dia a subprefeitura tem uma lista de chamados abertos (buracos, rachaduras, calçadas). A equipe
sai da base, passa por todos e volta. Escolher a ordem de visita com menor distância é o **problema do
caixeiro-viajante (TSP)**: com *n* chamados existem *n!* rotas possíveis.

| Chamados por equipe | Rotas possíveis | Qubits na formulação QUBO |
| --- | --- | --- |
| 5 | 120 | 25 |
| 8 | 40.320 | 64 |
| 10 | 3,6 milhões | 100 |
| 15 | 1,3 trilhão | 225 |
| 20 | 2,4 × 10¹⁸ | 400 |
| 50 | 3,0 × 10⁶⁴ | 2.500 |

Com o ZelaCidade em escala (todos os chamados da cidade, várias equipes, janelas de horário, prioridade
por gravidade), o problema vira um **roteamento de veículos (VRP)**, ainda mais difícil.

## O que o protótipo faz

`rota_qubo.py` usa 8 chamados simulados no centro de São Paulo (coordenadas aproximadas dos bairros,
distância em linha reta) e compara:

1. **Força bruta (clássico, exato):** testa as 40.320 rotas.
2. **Vizinho mais próximo (clássico, heurística):** sempre vai para o chamado mais perto.
3. **Formulação QUBO:** o mesmo problema escrito como minimização de energia sobre variáveis binárias
   `x[i,t]` (chamado *i* na posição *t*), com penalidades para que cada chamado e cada posição sejam
   usados uma única vez. É o formato aceito por **recozimento quântico** (ex.: D-Wave) e pelo **QAOA**.
4. **Recozimento simulado sobre o QUBO:** algoritmo clássico "inspirado em quântica", usado aqui como
   referência do que um annealer faria com a mesma formulação.

**Nenhum hardware nem simulador quântico foi usado.** O objetivo é mostrar a formulação, medir o
gargalo e embasar o roadmap.

```bash
python quantica/rota_qubo.py   # gera quantica/resultado.json
```

## Resultados (17/11/2026)

| Método | Chamados | Qubits | Distância | Ótimo? |
| --- | --- | --- | --- | --- |
| Força bruta | 8 | – | 24,86 km | Sim (referência), 0,24 s |
| Vizinho mais próximo | 8 | – | 28,65 km | Não, 15,2% mais longa |
| QUBO – enumeração das 65.536 combinações | 4 | 16 | 7,01 km | Sim: prova que a formulação está correta |
| QUBO – recozimento simulado | 4 | 16 | 7,01 km | Sim |
| QUBO – recozimento simulado | 6 | 36 | 13,88 km | Sim |
| QUBO – recozimento simulado | 8 | 64 | 25,63 km | Não, 3,1% acima do ótimo |

**Leitura honesta dos resultados:**
- Para o tamanho atual (8 chamados por equipe), o computador clássico resolve o problema **exato em
  menos de 1 segundo**. Hoje não há vantagem em usar computação quântica.
- A formulação QUBO funciona (o mínimo dela é a rota ótima), mas precisa de *n²* qubits: 64 qubits
  para 8 chamados. Isso já é demais para os computadores quânticos de porta atuais, que ainda têm muito
  ruído.
- A penalidade do QUBO precisa ser ajustada: valores muito altos deixam o recozimento preso em rotas
  ruins (testamos fatores 1,5, 2 e 3; ficou 1,5).

## Roadmap clássico × quântico

| Fase | Quando | Abordagem | Justificativa |
| --- | --- | --- | --- |
| 1 – Agora | Protótipo | Clássico: força bruta até ~10 chamados; heurística (vizinho mais próximo + 2-opt) ou solver como OR-Tools acima disso | Resolve o problema real com custo baixo e resultado auditável |
| 2 – Curto prazo | 1 a 2 anos | Inspirado em quântica: recozimento simulado / digital annealers sobre o mesmo QUBO, para o VRP com várias equipes | Usa a formulação QUBO já validada, sem depender de hardware quântico |
| 3 – Médio prazo | 3 a 5 anos | Híbrido: annealer quântico ou QAOA via nuvem para subproblemas (ex.: uma região por vez), com o clássico decidindo a divisão | Só adotar se um benchmark mostrar ganho de tempo ou de qualidade sobre o clássico |
| 4 – Segurança | Contínuo | Migrar a criptografia do app e da API para algoritmos pós-quânticos (PQC, padrões do NIST como ML-KEM) | Os chamados têm localização e fotos dos cidadãos; um ataque futuro "guarde agora, decifre depois" exporia esses dados |

## Ética, LGPD e ODS

- **LGPD:** a rota usa só o endereço do problema, não o do cidadão. Fotos e localização são dados
  pessoais quando ligadas a quem reportou; qualquer processamento em nuvem quântica de terceiros
  precisa de contrato de tratamento de dados e, se for fora do Brasil, das regras de transferência
  internacional.
- **Justiça na priorização:** otimizar só a distância favorece bairros centrais e concentrados.
  O peso da rota deve incluir gravidade e tempo de espera, para que bairros periféricos (Capão Redondo,
  Brasilândia, São Mateus) não fiquem sempre por último.
- **Transparência:** a ordem de atendimento tem que ser explicável ao cidadão; resultados de um
  solver quântico devem ser conferidos por um método clássico antes de ir para as equipes.
- **ODS 11** (cidades sustentáveis), **ODS 9** (infraestrutura e inovação) e **ODS 13** (menos
  quilômetros rodados, menos emissões).
