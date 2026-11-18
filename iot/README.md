# IoT – reconhecimento de sons para pessoas surdas

Modelo treinado no Edge Impulse (projeto `zelacidade-sons`) para reconhecer 3 classes de som da rua:
**sirene**, **buzina** e **ruído** (som normal do ambiente). A ideia é que um dispositivo (ou o celular)
avise a pessoa surda por vibração ou alerta visual quando ouvir uma sirene ou uma buzina.

## Como foi feito

- **Coleta:** amostras de 10 s gravadas com o microfone do celular, cerca de 2 min por classe.
  Sirene e buzina vieram de vídeos tocados em caixa de som; ruído é o som do ambiente.
- **Divisão:** 80% treino / 20% teste (Perform train/test split do Edge Impulse).
- **Impulse:** janela de 1000 ms com passo de 500 ms, bloco **Audio (MFE)** e bloco **Classification**
  (rede neural, 100 ciclos de treino, configuração padrão).

## Resultados

| Avaliação | Acurácia | Observação |
| --- | --- | --- |
| Validação (durante o treino) | 92,9% | Janelas tiradas das mesmas gravações do treino, por isso é otimista |
| Model testing (conjunto de teste) | 76,84% | Gravações que o modelo não viu; F1: buzina 0,82, ruído 0,43, sirene 0,88 |
| 15 testes ao vivo | 73,3% (11/15) | Sons tocados perto do microfone, 5 por classe, ver abaixo |

### Testes ao vivo

Feitos no navegador (Deployment > Launch in browser), tocando cada som por cerca de 5 segundos
perto do microfone e anotando a classe que venceu.
Detalhe em `testes_ao_vivo.csv`.

| Som tocado ↓ / Modelo respondeu → | buzina | ruído | sirene | Acertos |
| --- | --- | --- | --- | --- |
| **buzina** | 3 | 1 | 1 | 3/5 |
| **ruído** | 0 | 5 | 0 | 5/5 |
| **sirene** | 0 | 2 | 3 | 3/5 |

## Análise

- **Ruído** foi reconhecido em todos os testes: o modelo não gerou alarme falso no ambiente parado.
- O erro mais comum é **sirene ou buzina classificada como ruído** (3 dos 4 erros). Para uma pessoa surda
  esse é o erro mais grave, porque significa um alerta que não chegou.
- Causa provável: trechos de silêncio dentro das amostras de sirene e buzina (início dos vídeos, pausa
  entre buzinadas), que o Feature explorer mostra misturados com o ruído, e pouco dado (~2 min por classe).
- Os testes ao vivo (73,3%) ficaram próximos do Model testing (76,84%), o que indica que o número do
  teste representa bem o uso real. Ainda assim, 15 testes é uma amostra pequena.

## Melhorias possíveis

- Cortar os silêncios das amostras de sirene e buzina (Crop sample) e treinar de novo.
- Gravar mais dados, com sirenes e buzinas variadas e em ambientes diferentes (rua, chuva, trânsito).
- Usar um limiar de confiança menor para sirene: é melhor um alarme falso do que um alerta perdido.
- Exigir duas janelas seguidas da mesma classe antes de alertar, para reduzir oscilação.

## Evidências

| Arquivo | O que mostra |
| --- | --- |
| `feature_explorer.png` | Separação das 3 classes depois do bloco MFE |
| `treino_validacao.png` | Acurácia de 92,9% e matriz de confusão da validação |
| `treino_data_explorer.png` | Amostras de validação classificadas, com os erros em vermelho |
| `model_testing.png` | Acurácia de 76,84% e matriz de confusão do conjunto de teste |
| `ao_vivo_ruido.png`, `ao_vivo_buzina.png`, `ao_vivo_sirene.png` | Classificação ao vivo no navegador, uma tela por classe |
