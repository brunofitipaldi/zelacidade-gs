# GenAI – assistente do ZelaCidade

Assistente que responde dúvidas sobre calçadas, tapa-buraco e o próprio app usando só os
documentos tratados pelo módulo de PLN (`pln/corpus/texto_puro.jsonl`).

```bash
python genai/assistente.py "Qual a largura mínima da faixa livre?"
python genai/avaliar.py            # avaliação sem custo (modo extrativo)
python genai/avaliar.py --claude   # avaliação com o Claude (precisa de ANTHROPIC_API_KEY; gera custo)
```

## Como funciona

1. **Busca (BM25):** encontra os 3 trechos mais parecidos com a pergunta. O título da seção pesa em dobro.
2. **Trava contra respostas sem base:** se o melhor trecho tiver relevância abaixo de 4,0 ou menos de
   2 termos em comum com a pergunta, o assistente responde que não encontrou a informação e indica o SP156.
3. **Resposta:**
   - **extrativo** (padrão): devolve frases do próprio documento, com a fonte. Não gera texto novo.
   - **claude** (opcional): com `ANTHROPIC_API_KEY` configurada, o modelo `claude-opus-5-5` redige a
     resposta usando apenas os trechos encontrados, com esforço `low` e fallback automático do servidor
     em caso de recusa. Sem rede ou sem crédito, volta para o modo extrativo.

## Avaliação (modo extrativo, 16/11/2026)

21 perguntas em `casos_teste.json`: 15 dentro do escopo e 6 fora (metrô, RG, IPTU, futebol, CNH, clima).

| Métrica | Resultado |
| --- | --- |
| Documento certo em 1º lugar (busca@1) | 15/15 (100%) |
| Resposta contém a informação esperada | 14/15 (93%) |
| Perguntas do escopo recusadas por engano | 0/15 |
| Perguntas fora do escopo recusadas | 6/6 (100%) |
| Respostas sem base (fora do escopo respondidas) | 0/6 |

Detalhe de cada pergunta em `resultado_avaliacao_extrativo.json`.

## Limitações conhecidas

- O conjunto de teste é pequeno (21 perguntas) e foi escrito pela própria equipe, olhando os documentos.
  Os números servem para comparar versões, não como medida geral de qualidade.
- A métrica de busca confere o **documento**, não a seção. Exemplo: "Qual a largura mínima da faixa livre?"
  responde com a seção "Calçadas estreitas", que cita 1,20 m, e não com a seção "Faixa livre".
- "O que preciso informar quando pedir o tapa-buraco?" trouxe a introdução da página, e não a seção
  "O que informar no pedido?". A busca por palavras não liga "pedir" a "pedido".
- O mascaramento de telefone do PLN também apagou o WhatsApp oficial do SP156, que é um número público.
  É um falso positivo da proteção de dados.
- O modo extrativo só copia trechos. Ele não junta informações de seções diferentes nem reescreve em
  linguagem mais simples.
