# ZelaCidade

Protótipo CitizenTech da Global Solution 2026.2 (FIAP, turma 2TIAPY).

O cidadão fotografa um problema urbano (buraco, rachadura, calçada quebrada), a solução
classifica a imagem, registra um chamado e avisa a prefeitura. Um assistente responde
dúvidas sobre serviços públicos, e uma aba de alertas mostra sons da rua para pessoas
com deficiência auditiva.

Autor: Bruno Lanchariche Fitipaldi Lopes – RM 564129

## Módulos

| Pasta | Disciplina | O que faz | Status |
| --- | --- | --- | --- |
| `app/` | Front End & Mobile Development | Interface Streamlit que integra os módulos | Em desenvolvimento |
| `rpa/` | AI for Robotic Process Automation | Trata as detecções com Pandas, grava no SQLite e gera o e-mail para a prefeitura | Em desenvolvimento |
| `pln/` | PLN, Chatbots & Virtual Agents | Limpa documentos e gera os 3 corpus | Pronto (falta rodar com os PDFs da prefeitura) |
| `genai/` | Generative AI & Advanced Nets | Assistente que responde com base no corpus | A fazer |
| `visao/` | Visão Computacional | Classifica fotos de problemas urbanos | A fazer |
| `quantica/` | Computação Quântica & IA | Roadmap e exemplo de otimização de rota | A fazer |
| `cluster/` | Cluster Computing | Simulação no iSPD | A fazer |
| `iot/` | Physical Computing & IoT | Reconhecimento de sons no Edge Impulse | A fazer |
| `docs/` | Governança em IA | Relatório, prints e link do vídeo | A fazer |

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python rpa/rpa_chamados.py
streamlit run app/app.py
```

## Dados

Os dados de chamados em `data/deteccoes_exemplo.csv` são **simulados** e servem só para
testar o fluxo. Nenhum dado pessoal real é usado.
