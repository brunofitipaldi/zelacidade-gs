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
| `app/` | Front End & Mobile Development | Interface Streamlit com 4 abas que integra os módulos; Dockerfile para deploy | Pronto |
| `rpa/` | AI for Robotic Process Automation | Trata as detecções com Pandas, grava no SQLite e gera o e-mail para a prefeitura | Pronto e integrado ao app |
| `pln/` | PLN, Chatbots & Virtual Agents | Limpa documentos e gera os 3 corpus | Pronto |
| `genai/` | Generative AI & Advanced Nets | Assistente que responde com base no corpus | Pronto e integrado ao app |
| `visao/` | Visão Computacional | Classifica a foto em buraco, rachadura ou desgaste do asfalto (85% no teste) | Pronto e integrado ao app |
| `quantica/` | Computação Quântica & IA | Rota das equipes: força bruta × heurística × formulação QUBO, e roadmap | Pronto |
| `cluster/` | Cluster Computing | 14 cenários no iSPD: nós, rede e escalonador para um pico de 1000 fotos | Pronto |
| `iot/` | Physical Computing & IoT | Reconhecimento de sons no Edge Impulse (sirene, buzina, ruído) | Resultados na aba Alertas; alerta ao vivo para o app não integrado |
| `docs/` | Governança em IA | Figuras do relatório (o relatório e o vídeo são entregues no portal da FIAP) | Em andamento |

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
python rpa/rpa_chamados.py
streamlit run app/app.py
```

### Com Docker

```bash
docker build -t zelacidade .
docker run -p 8501:8501 zelacidade
```

Depois abra http://localhost:8501. A imagem instala o PyTorch só CPU, baixa os pesos da MobileNetV3
durante o build (o container sobe sem internet), roda o RPA para popular o banco com os chamados
simulados e inicia o Streamlit sem usuário root. Para o RPA enviar e-mail de verdade, passe as
variáveis `ZELA_SMTP_HOST`, `ZELA_SMTP_PORT`, `ZELA_SMTP_USER`, `ZELA_SMTP_SENHA`, `ZELA_EMAIL_DE` e
`ZELA_EMAIL_PARA` com `-e`.

## Dados

Os dados de chamados em `data/deteccoes_exemplo.csv` são **simulados** e servem só para
testar o fluxo. Nenhum dado pessoal real é usado.

Documentos em `docs_fonte/` (públicos, baixados em 16/11/2026):

- Cartilha de Calçadas 2026 – Secretaria Municipal da Pessoa com Deficiência, Prefeitura de São Paulo
- "Operação Tapa-Buraco no Ipiranga: saiba como solicitar o serviço" – Subprefeitura Ipiranga
- Página "Calçadas" – Secretaria Municipal das Subprefeituras
- FAQ do ZelaCidade – escrito pela equipe do projeto

Fotos para a visão computacional: *Multiclass Road Surface Damage Classification Dataset* (Mendeley
Data, doi 10.17632/697w4jkr2x.2), baixado em 17/11/2026. Fica em `data/visao_dataset/` e não vai para
o repositório; veja `visao/README.md` para baixar e treinar de novo.
