"""
Entrega 1 — analise lexica.

Transformar o texto do programa numa lista de tokens.

O que voces tem que devolver: uma lista de Token. O ultimo elemento e sempre
um token FIM_ARQUIVO. A regra de posicao dele esta em CONTRATOS.md, secao 7.

Leiam antes: LINGUAGEM.md secao 2, e CONTRATOS.md secao 2.
"""
from mplc.erros import ErroMPL


class Token:
    __slots__ = ('tipo', 'lexema', 'linha', 'coluna')

    def __init__(self, tipo, lexema, linha, coluna):
        self.tipo = tipo          # 'ID', 'INTEIRO', 'MAIS', ... (a lista esta no contrato)
        self.lexema = lexema      # o texto exato como apareceu no fonte
        self.linha = linha
        self.coluna = coluna      # a coluna do PRIMEIRO caractere do token

    def __str__(self):
        # esta e a linha que o --tokens imprime; nao mexam no formato
        return f"{self.linha},{self.coluna},{self.tipo},{self.lexema}"


def analisar(fonte):
    """Recebe o texto do programa. Devolve a lista de Token."""
    tokens = []
    i = 0
    linha = 1
    coluna = 1
    tamanho = len(fonte)

    palavras = {
        'funcao': 'FUNCAO', 'retorne': 'RETORNE', 'se': 'SE',
        'senao': 'SENAO', 'enquanto': 'ENQUANTO', 'escreva': 'ESCREVA',
        'inteiro': 'TIPO_INTEIRO', 'real': 'TIPO_REAL',
        'logico': 'TIPO_LOGICO', 'texto': 'TIPO_TEXTO',
        'vazio': 'TIPO_VAZIO', 'verdadeiro': 'LOGICO', 'falso': 'LOGICO',
        'e': 'E', 'ou': 'OU', 'nao': 'NAO',
    }
    simbolos_duplos = {
        '==': 'IGUAL', '!=': 'DIFERENTE',
        '<=': 'MENOR_IGUAL', '>=': 'MAIOR_IGUAL',
    }
    simbolos_simples = {
        '+': 'MAIS', '-': 'MENOS', '*': 'VEZES', '/': 'DIVIDE',
        '%': 'RESTO', '<': 'MENOR', '>': 'MAIOR', '=': 'ATRIBUI',
        '(': 'ABRE_PAR', ')': 'FECHA_PAR',
        '{': 'ABRE_CHAVE', '}': 'FECHA_CHAVE',
        ',': 'VIRGULA', ';': 'PONTO_VIRGULA',
    }

    def e_letra(caractere):
        return ('a' <= caractere <= 'z' or
                'A' <= caractere <= 'Z' or caractere == '_')

    def e_digito(caractere):
        return '0' <= caractere <= '9'

    while i < tamanho:
        caractere = fonte[i]

        if caractere in ' \t\r':
            i += 1
            coluna += 1
            continue
        if caractere == '\n':
            i += 1
            linha += 1
            coluna = 1
            continue

        inicio = i
        linha_inicio = linha
        coluna_inicio = coluna

        if fonte.startswith('//', i):
            i += 2
            coluna += 2
            while i < tamanho and fonte[i] != '\n':
                i += 1
                coluna += 1
            continue

        if fonte.startswith('/*', i):
            i += 2
            coluna += 2
            while i < tamanho and not fonte.startswith('*/', i):
                if fonte[i] == '\n':
                    i += 1
                    linha += 1
                    coluna = 1
                else:
                    i += 1
                    coluna += 1
            if i == tamanho:
                raise ErroMPL('lexico', linha_inicio, coluna_inicio,
                              'comentario de bloco nao foi fechado')
            i += 2
            coluna += 2
            continue

        if e_letra(caractere):
            i += 1
            coluna += 1
            while i < tamanho and (e_letra(fonte[i]) or e_digito(fonte[i])):
                i += 1
                coluna += 1
            lexema = fonte[inicio:i]
            tokens.append(Token(palavras.get(lexema, 'ID'), lexema,
                                linha_inicio, coluna_inicio))
            continue

        if e_digito(caractere):
            i += 1
            coluna += 1
            while i < tamanho and e_digito(fonte[i]):
                i += 1
                coluna += 1
            tipo = 'INTEIRO'
            if i < tamanho and fonte[i] == '.':
                linha_ponto, coluna_ponto = linha, coluna
                if i + 1 >= tamanho or not e_digito(fonte[i + 1]):
                    raise ErroMPL('lexico', linha_ponto, coluna_ponto,
                                  'o ponto de um real exige digitos dos dois lados')
                tipo = 'REAL'
                i += 1
                coluna += 1
                while i < tamanho and e_digito(fonte[i]):
                    i += 1
                    coluna += 1
            tokens.append(Token(tipo, fonte[inicio:i], linha_inicio, coluna_inicio))
            continue

        if caractere == '"':
            i += 1
            coluna += 1
            while i < tamanho and fonte[i] != '"':
                if fonte[i] in '\n\r':
                    raise ErroMPL('lexico', linha_inicio, coluna_inicio,
                                  'literal de texto nao foi fechado')
                if fonte[i] == '\\':
                    coluna_escape = coluna
                    if i + 1 >= tamanho or fonte[i + 1] not in 'nt"\\':
                        raise ErroMPL('lexico', linha, coluna_escape,
                                      'escape invalido em literal de texto')
                    i += 2
                    coluna += 2
                else:
                    i += 1
                    coluna += 1
            if i == tamanho:
                raise ErroMPL('lexico', linha_inicio, coluna_inicio,
                              'literal de texto nao foi fechado')
            i += 1
            coluna += 1
            tokens.append(Token('TEXTO', fonte[inicio:i],
                                linha_inicio, coluna_inicio))
            continue

        lexema_duplo = fonte[i:i + 2]
        if lexema_duplo in simbolos_duplos:
            tokens.append(Token(simbolos_duplos[lexema_duplo], lexema_duplo,
                                linha_inicio, coluna_inicio))
            i += 2
            coluna += 2
            continue
        if caractere in simbolos_simples:
            tokens.append(Token(simbolos_simples[caractere], caractere,
                                linha_inicio, coluna_inicio))
            i += 1
            coluna += 1
            continue

        raise ErroMPL('lexico', linha, coluna,
                      f'caractere inesperado {caractere!r}')

    tokens.append(Token('FIM_ARQUIVO', '', linha, coluna))
    return tokens
