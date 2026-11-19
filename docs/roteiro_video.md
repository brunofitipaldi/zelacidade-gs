# Roteiro do vídeo – ZelaCidade (6 min 30 s)

> **Não leia na hora de gravar.** O enunciado tira metade da nota do vídeo se houver leitura de texto.
> Use as falas para ensaiar duas ou três vezes; na gravação, olhe só os **pontos-chave** de cada bloco
> e fale do seu jeito. Errou uma palavra? Siga em frente, fica mais natural.

## Antes de gravar (10 min)

1. Abra o terminal na pasta do projeto e rode:
   ```bash
   .venv\Scripts\activate
   python rpa/rpa_chamados.py
   streamlit run app/app.py
   ```
2. Deixe abertas, em abas do navegador:
   - o app (http://localhost:8501);
   - o GitHub: https://github.com/brunofitipaldi/zelacidade-gs;
   - o Edge Impulse logado, em **Deployment > Launch in browser**;
   - o relatório em Word (para mostrar o Quadro 1 e os gráficos).
3. Separe no celular um vídeo de **sirene** para tocar no teste do IoT.
4. Tenha à mão uma foto de buraco para enviar no app. Pode usar
   `data/visao_dataset/Dataset/Pothole/188.jpg` (o modelo acerta essa com 94%).
5. Grave a tela com o **Clipchamp** ou o **OBS**, de preferência por blocos, e junte no final.

---

## Bloco 1 – Abertura (0:00–0:30)

**Na tela:** você (câmera) ou a capa do relatório.

**Pontos-chave:** nome e RM · projeto ZelaCidade · problema em uma frase.

**Fala-guia:**
"Oi, eu sou o Bruno, RM 564129, da turma 2TIAPY. Esse é o ZelaCidade, meu projeto da Global Solution.
A ideia é simples: o cidadão vê um buraco ou uma calçada quebrada, tira uma foto, e a inteligência
artificial cuida do resto, até o chamado chegar na prefeitura."

## Bloco 2 – Problema e cidadão (0:30–1:00)

**Na tela:** a foto do buraco.

**Pontos-chave:** quem sofre (cadeirante, idoso, carrinho de bebê) · SP156 é difícil · ODS 9, 10 e 11.

**Fala-guia:**
"Pra maioria das pessoas um buraco na calçada é só um incômodo. Pra quem usa cadeira de rodas ou anda de
bengala, pode impedir de sair de casa. Hoje o pedido de conserto é pelo SP156, mas a pessoa precisa saber
descrever o problema e acompanhar o pedido. O projeto conversa com os ODS 9, 10 e 11: infraestrutura,
redução de desigualdades e cidades sustentáveis."

## Bloco 3 – Visão geral (1:00–1:40)

**Na tela:** README do GitHub, na tabela de módulos.

**Pontos-chave:** foto → visão → RPA → prefeitura · assistente com PLN · alertas sonoros · cluster e
quântica como estudos.

**Fala-guia:**
"O fluxo é esse: a foto passa pela visão computacional, que sugere o tipo do problema. Um robô de RPA
valida, grava o chamado no banco e avisa a prefeitura por e-mail. Tem um assistente que tira dúvidas
usando documentos oficiais, que foram tratados pelo módulo de PLN. E tem uma aba de alertas pra pessoas
surdas, com sons da rua. Cluster e computação quântica entraram como estudo de escala, pra quando o app
fosse usado na cidade inteira."

## Bloco 4 – Aplicativo e visão computacional (1:40–2:40)

**Na tela:** app aberto → **Reportar problema** → enviar a foto → depois o **Painel**.

**Pontos-chave:** sugestão + confiança · cidadão confirma ou troca · 85% no teste · ~40 ms ·
abaixo de 60% vai para revisão humana.

**Fala-guia (enquanto envia a foto):**
"Vou mandar essa foto de um buraco. Em menos de um segundo a IA sugere 'buraco na via' com 94% de
confiança e mostra a probabilidade de cada tipo. Mas quem decide é o cidadão: ele pode trocar o tipo
antes de enviar."

**(abre o Painel)**
"Aqui no painel ficam os chamados. Esses dois estão em revisão humana porque a confiança da IA ficou
abaixo de 60%. Alguém precisa aprovar ou descartar. O modelo é uma MobileNetV3, pequena e rápida,
e acertou 85% das fotos de teste. Quando limpei o dataset, achei 44 fotos com o rótulo errado, e isso
mostrou que até o dado de treino precisa ser conferido."

## Bloco 5 – Assistente (2:40–3:10)

**Na tela:** aba **Assistente**. Pergunte, nesta ordem:
1. "Como peço o conserto de um buraco na rua?"
2. "Qual o valor do IPTU da minha casa?"

**Pontos-chave:** responde só com documentos oficiais · mostra a fonte · recusa o que não sabe ·
6 de 6 perguntas fora do escopo recusadas, nenhuma alucinação.

**Fala-guia:**
"O assistente responde só com base em documentos oficiais da prefeitura e mostra de onde tirou a
resposta. Agora uma pergunta fora do assunto, sobre IPTU: ele não inventa, diz que não encontrou e manda
pro SP156. Nos testes, ele recusou as seis perguntas fora do escopo e não inventou nenhuma resposta."

## Bloco 6 – IoT (3:10–3:45)

**Na tela:** Edge Impulse no navegador → toque a sirene no celular → depois a aba **Alertas sonoros**.

**Pontos-chave:** sirene, buzina e ruído · 76,84% no teste · 3 alertas perdidos em 10 · testes ao vivo
com os mesmos vídeos do treino.

**Fala-guia:**
"Esse é o modelo de sons que eu treinei no Edge Impulse, com sirene, buzina e ruído. Vou tocar uma
sirene… e ele reconhece. No teste ele acertou 76,84%. Mas o que mais me preocupou foi o tipo de erro:
em 3 de 10 vezes ele achou que sirene ou buzina era só ruído, e pra uma pessoa surda isso é um alerta
que não chega. E os testes ao vivo eu fiz com os mesmos vídeos do treino, então o número que vale
mesmo é o do teste."

## Bloco 7 – RPA e PLN (3:45–4:20)

**Na tela:** terminal rodando `python rpa/rpa_chamados.py` → depois a pasta `pln/corpus`.

**Pontos-chave:** Pandas + SQL + e-mail · 15 aceitos, 5 rejeitados com motivo · 3 corpus.

**Fala-guia:**
"O robô de RPA usa Pandas pra limpar os dados, SQLite pra gravar e e-mail pra avisar a prefeitura.
Das 20 detecções de teste, ele aceitou 15 e rejeitou 5, cada uma com o motivo. Se o e-mail falha, ele
tenta de novo e salva a mensagem, então nada se perde. Já o PLN limpou os documentos da prefeitura e
gerou três corpus: texto puro, perguntas e respostas e conversacional, que é a base do assistente."

## Bloco 8 – Cluster e quântica (4:20–5:00)

**Na tela:** Figura 1 do relatório (gráfico do cluster) → Tabela 2 (rota).

**Pontos-chave:** 1 Gbps: 22 s com 2, 4 ou 8 nós · gargalo é a rede · 10 Gbps escala · rota da equipe
como QUBO · hoje o clássico resolve em menos de 1 s.

**Fala-guia:**
"No iSPD eu simulei 1000 fotos chegando juntas. Com rede de 1 gigabit, 2, 4 ou 8 máquinas levam os
mesmos 22 segundos, porque o gargalo é a rede. Com 10 gigabits, aí sim o cluster escala. Na quântica,
o problema é a rota da equipe de manutenção. Escrevi o problema no formato QUBO, que é o que computador
quântico usa, e vi que hoje o computador clássico resolve em menos de um segundo. Então a computação
quântica entra no roadmap, não agora."

## Bloco 9 – Governança (5:00–6:00)

**Na tela:** Quadro 1 do relatório.

**Pontos-chave:** 5 integrados, IoT parcial, 2 estudos · LGPD: sem dados pessoais, mas a foto pode ter
rosto e placa · humano decide · uso de IA declarado.

**Fala-guia:**
"Juntando tudo: cinco módulos rodam no app, o IoT entrou em parte e cluster e quântica ficaram como
estudo. Na LGPD, o chamado não guarda nome nem CPF, mas a foto pode mostrar rosto ou placa de carro,
e isso ainda precisa ser tratado. O maior risco é o alerta perdido do IoT, então o app não pode ser o
único aviso. Por isso, em todo o projeto, a IA sugere e uma pessoa decide. E eu declarei no relatório
onde usei IA pra me ajudar e o que foi feito por mim."

## Bloco 10 – Fechamento (6:00–6:30)

**Na tela:** repositório no GitHub.

**Pontos-chave:** resultado em uma frase · código no GitHub · obrigado.

**Fala-guia:**
"O ZelaCidade mostrou que dá pra juntar várias áreas de IA numa solução só, desde que dê pra confiar
nela, com testes, transparência e revisão humana. O código, os resultados e o relatório estão no
GitHub. Obrigado!"

---

## Dicas finais

- **Cronometre o ensaio.** Tem que ficar entre 5 e 7 minutos.
- Fale mostrando a tela funcionando. O professor quer ver o app rodando.
- Ao subir no YouTube, marque **"Não listado"**, copie o link e cole na seção 4 do relatório.
