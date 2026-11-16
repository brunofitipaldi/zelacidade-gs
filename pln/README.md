# PLN – preparação de corpus

Lê os documentos da pasta `docs_fonte/` (PDF, DOCX, TXT, MD, HTML), limpa o texto e gera
três corpus para fine-tuning de uma LLM de pequeno porte.

```bash
python pln/preparar_corpus.py            # docs_fonte/ -> pln/corpus/
python pln/teste_limpeza.py              # testes da limpeza (rodar de dentro de pln/)
```

## Limpeza e normalização

1. Normalização Unicode (NFC), ligaduras de PDF (ﬁ, ﬂ), espaços especiais e aspas.
2. Remoção de cabeçalhos e rodapés que se repetem nas páginas.
3. Remoção de números de página ("3", "Página 3 de 10").
4. Correção de palavras quebradas com hífen no fim da linha.
5. Junção de linhas quebradas em parágrafos e detecção de títulos.
6. Mascaramento de dados pessoais: e-mail, CPF e telefone viram `[EMAIL]`, `[CPF]`, `[TELEFONE]`.
7. Remoção de parágrafos duplicados e de trechos com menos de 30 caracteres.

## Saída (`pln/corpus/`)

| Arquivo | Formato | Uso |
| --- | --- | --- |
| `texto_puro.jsonl` | `{"text", "fonte"}` | Pré-treino contínuo / adaptação de domínio |
| `perguntas_respostas.jsonl` | `{"pergunta", "resposta", "fonte", "origem"}` | Fine-tuning de instrução e base do assistente |
| `conversacional.jsonl` | `{"messages": [system, user, assistant]}` | Fine-tuning de chat (formato aceito por OpenAI, Hugging Face TRL e outros) |
| `*_treino.jsonl`, `*_validacao.jsonl` | mesmo formato | Divisão 90/10 com semente fixa |
| `relatorio.json` | JSON | Quantidades removidas, mascaradas e geradas |

As perguntas vêm de três regras: títulos de seção, frases de definição ("X é ...") e frases
de obrigação ("deve", "é proibido"). Todas as respostas são trechos do próprio documento, sem
texto inventado, e trazem a fonte.
