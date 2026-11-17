"""Testes da limpeza do PLN com um documento de 3 páginas montado à mão.

Rodar: python pln/teste_limpeza.py
"""

import preparar_corpus as pc

PAGINAS = [
    "PREFEITURA DE EXEMPLO – MANUAL DE CALÇADAS\n"
    "1. RESPONSABILIDADE\n"
    "A manutenção da calçada em frente ao imóvel é responsabi-\n"
    "lidade do proprietário. O proprietário deve manter o piso\n"
    "regular e sem buracos.\n"
    "Em caso de dúvida, o munícipe pode falar com o atendimento pelo e-mail fulano@exemplo.com ou pelo telefone (11) 98765-4321.\n"
    "1",
    "PREFEITURA DE EXEMPLO – MANUAL DE CALÇADAS\n"
    "2. FAIXA LIVRE\n"
    "Faixa livre é a área da calçada destinada exclusivamente à circulação de pedestres.\n"
    "Ela deve ter largura mínima de 1,20 metro.\n"
    "2",
    "PREFEITURA DE EXEMPLO – MANUAL DE CALÇADAS\n"
    "3. RAMPAS\n"
    "As rampas devem ter inclinação máxima de 8,33%. O CPF 123.456.789-09 é só um exemplo.\n"
    "Página 3 de 3",
]


def main():
    est = pc.Estatisticas()
    paginas = [pc.normalizar(p) for p in PAGINAS]
    linhas = [l for pag in pc.remover_repetidas(paginas, est) for l in pag + [""]]
    secoes = pc.limpar_paragrafos(pc.montar_secoes(linhas, est), est, set())
    texto = " ".join(p for _, ps in secoes for p in ps)
    titulos = [t for t, _ in secoes]

    checagens = {
        "cabeçalho repetido removido (3x)": est.cabecalhos_rodapes == 3 and "MANUAL DE CALÇADAS" not in texto,
        "números de página removidos (3x)": est.numeros_pagina == 3,
        "hifenização corrigida": "responsabilidade do proprietário" in texto,
        "e-mail mascarado": "[EMAIL]" in texto and "@" not in texto,
        "telefone mascarado": "[TELEFONE]" in texto and "98765" not in texto,
        "CPF mascarado": "[CPF]" in texto and "123.456" not in texto,
        "títulos detectados": titulos == ["Responsabilidade", "Faixa livre", "Rampas"],
    }
    pares = pc.gerar_perguntas([("manual_calcadas.pdf", secoes)])
    perguntas = [p["pergunta"] for p in pares]
    checagens["definição igual ao título não vira pergunta repetida"] = "O que é faixa livre?" not in perguntas
    checagens["pergunta de regra gerada"] = "Quais são as regras sobre rampas?" in perguntas

    for nome, ok in checagens.items():
        print(("OK   " if ok else "FALHA"), nome)
    print("\nPerguntas geradas:", *perguntas, sep="\n  ")
    assert all(checagens.values()), "Alguma checagem falhou"


if __name__ == "__main__":
    main()
