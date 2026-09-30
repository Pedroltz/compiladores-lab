"""
Entrega 2 — analise sintatica.

Transformar a lista de tokens numa arvore.

Sugestao forte: descida recursiva, uma funcao por nivel de precedencia, na
ordem da secao 3.3 da especificacao. E como voces vao enxergar a precedencia
virar formato de arvore.

Gerador de parser (ANTLR, PLY, yacc) esta proibido nesta entrega e na
anterior — o objetivo e entender, e o gerador esconde exatamente a parte
que esta sendo ensinada.

Leiam antes: LINGUAGEM.md secoes 3 a 5, e CONTRATOS.md secao 3.
"""
from mplc.erros import ErroMPL


class No:
    """Um no da arvore. O rotulo e o que sai no --ast."""

    def __init__(self, rotulo, filhos=None, linha=0, coluna=0, **extra):
        self.rotulo = rotulo      # 'binario +', 'literal inteiro 1', 'bloco', ...
        self.filhos = filhos or []
        self.linha = linha
        self.coluna = coluna
        self.extra = extra        # o que a semantica quiser pendurar depois


def analisar(tokens):
    """Recebe a lista de Token. Devolve a raiz da arvore (um No 'programa')."""
    # O indice fica fechado nesta funcao para que cada regra da gramatica
    # possa consumir somente os tokens que lhe pertencem.
    indice = 0

    def atual():
        return tokens[indice]

    def aceitar(tipo):
        nonlocal indice
        if atual().tipo == tipo:
            token = atual()
            indice += 1
            return token
        return None

    def esperar(tipo, esperado=None):
        nonlocal indice
        token = atual()
        if token.tipo != tipo:
            nome = esperado or tipo.lower().replace('_', ' ')
            raise ErroMPL('sintatico', token.linha, token.coluna,
                          f'esperava {nome}, encontrei {token.lexema or "fim do arquivo"}')
        indice += 1
        return token

    def tipo(permite_vazio=True):
        token = atual()
        tipos = {
            'TIPO_INTEIRO': 'inteiro', 'TIPO_REAL': 'real',
            'TIPO_LOGICO': 'logico', 'TIPO_TEXTO': 'texto',
            'TIPO_VAZIO': 'vazio',
        }
        if token.tipo not in tipos or (not permite_vazio and token.tipo == 'TIPO_VAZIO'):
            raise ErroMPL('sintatico', token.linha, token.coluna,
                          'esperava um tipo')
        esperar(token.tipo)
        return tipos[token.tipo], token

    def primario():
        token = atual()
        if token.tipo == 'ABRE_PAR':
            esperar('ABRE_PAR', "'('")
            no = expressao()
            esperar('FECHA_PAR', "')'")
            return no
        literais = {
            'INTEIRO': 'inteiro', 'REAL': 'real', 'LOGICO': 'logico',
            'TEXTO': 'texto',
        }
        if token.tipo in literais:
            esperar(token.tipo)
            valor = token.lexema
            if token.tipo == 'REAL':
                valor = f'{float(valor):.6f}'
            return No(f'literal {literais[token.tipo]} {valor}',
                      linha=token.linha, coluna=token.coluna,
                      tipo=literais[token.tipo], valor=valor)
        if token.tipo == 'ID':
            nome = esperar('ID')
            if not aceitar('ABRE_PAR'):
                return No(f'variavel {nome.lexema}', linha=nome.linha,
                          coluna=nome.coluna, nome=nome.lexema)
            argumentos = []
            if atual().tipo != 'FECHA_PAR':
                argumentos.append(expressao())
                while aceitar('VIRGULA'):
                    argumentos.append(expressao())
            esperar('FECHA_PAR', "')'")
            return No(f'chamada {nome.lexema}', argumentos, linha=nome.linha,
                      coluna=nome.coluna, nome=nome.lexema)
        raise ErroMPL('sintatico', token.linha, token.coluna,
                      'esperava uma expressao')

    # Cada nivel chama o imediatamente mais forte. Os lacos tornam os
    # operadores binarios associativos a esquerda; os unarios chamam o mesmo
    # nivel, portanto sao associativos a direita.
    def unario():
        token = atual()
        if token.tipo in ('NAO', 'MENOS'):
            esperar(token.tipo)
            op = 'nao' if token.tipo == 'NAO' else '-'
            return No(f'unario {op}', [unario()], linha=token.linha,
                      coluna=token.coluna, op=op)
        return primario()

    def multiplicativa():
        no = unario()
        operadores = {'VEZES': '*', 'DIVIDE': '/', 'RESTO': '%'}
        while atual().tipo in operadores:
            token = atual()
            esperar(token.tipo)
            no = No(f'binario {operadores[token.tipo]}', [no, unario()],
                    linha=token.linha, coluna=token.coluna,
                    op=operadores[token.tipo])
        return no

    def aditiva():
        no = multiplicativa()
        operadores = {'MAIS': '+', 'MENOS': '-'}
        while atual().tipo in operadores:
            token = atual()
            esperar(token.tipo)
            no = No(f'binario {operadores[token.tipo]}', [no, multiplicativa()],
                    linha=token.linha, coluna=token.coluna,
                    op=operadores[token.tipo])
        return no

    def relacional():
        no = aditiva()
        operadores = {'MENOR': '<', 'MENOR_IGUAL': '<=', 'MAIOR': '>',
                     'MAIOR_IGUAL': '>='}
        while atual().tipo in operadores:
            token = atual()
            esperar(token.tipo)
            no = No(f'binario {operadores[token.tipo]}', [no, aditiva()],
                    linha=token.linha, coluna=token.coluna,
                    op=operadores[token.tipo])
        return no

    def igualdade():
        no = relacional()
        operadores = {'IGUAL': '==', 'DIFERENTE': '!='}
        while atual().tipo in operadores:
            token = atual()
            esperar(token.tipo)
            no = No(f'binario {operadores[token.tipo]}', [no, relacional()],
                    linha=token.linha, coluna=token.coluna,
                    op=operadores[token.tipo])
        return no

    def conjuncao():
        no = igualdade()
        while atual().tipo == 'E':
            token = esperar('E')
            no = No('binario e', [no, igualdade()], linha=token.linha,
                    coluna=token.coluna, op='e')
        return no

    def expressao():
        no = conjuncao()
        while atual().tipo == 'OU':
            token = esperar('OU')
            no = No('binario ou', [no, conjuncao()], linha=token.linha,
                    coluna=token.coluna, op='ou')
        return no

    def bloco():
        abre = esperar('ABRE_CHAVE', "'{'")
        comandos = []
        while atual().tipo not in ('FECHA_CHAVE', 'FIM_ARQUIVO'):
            comandos.append(comando())
        esperar('FECHA_CHAVE', "'}'")
        return No('bloco', comandos, linha=abre.linha, coluna=abre.coluna)

    def comando():
        token = atual()
        if token.tipo == 'ABRE_CHAVE':
            return bloco()
        if token.tipo in ('TIPO_INTEIRO', 'TIPO_REAL', 'TIPO_LOGICO', 'TIPO_TEXTO'):
            nome_tipo, inicio = tipo()
            nome = esperar('ID', 'um identificador')
            filhos = []
            if aceitar('ATRIBUI'):
                filhos.append(expressao())
            esperar('PONTO_VIRGULA', "';'")
            return No(f'declaracao {nome.lexema} {nome_tipo}', filhos,
                      linha=inicio.linha, coluna=inicio.coluna,
                      nome=nome.lexema, tipo=nome_tipo)
        if token.tipo == 'ID':
            nome = esperar('ID')
            if aceitar('ATRIBUI'):
                valor = expressao()
                esperar('PONTO_VIRGULA', "';'")
                return No(f'atribuicao {nome.lexema}', [valor], linha=nome.linha,
                          coluna=nome.coluna, nome=nome.lexema)
            esperar('ABRE_PAR', "'=' ou '('")
            argumentos = []
            if atual().tipo != 'FECHA_PAR':
                argumentos.append(expressao())
                while aceitar('VIRGULA'):
                    argumentos.append(expressao())
            esperar('FECHA_PAR', "')'")
            esperar('PONTO_VIRGULA', "';'")
            return No(f'chamada {nome.lexema}', argumentos, linha=nome.linha,
                      coluna=nome.coluna, nome=nome.lexema)
        if token.tipo == 'SE':
            inicio = esperar('SE')
            esperar('ABRE_PAR', "'('")
            condicao = expressao()
            esperar('FECHA_PAR', "')'")
            filhos = [condicao, bloco()]
            if aceitar('SENAO'):
                filhos.append(bloco())
            return No('se', filhos, linha=inicio.linha, coluna=inicio.coluna)
        if token.tipo == 'ENQUANTO':
            inicio = esperar('ENQUANTO')
            esperar('ABRE_PAR', "'('")
            condicao = expressao()
            esperar('FECHA_PAR', "')'")
            return No('enquanto', [condicao, bloco()], linha=inicio.linha,
                      coluna=inicio.coluna)
        if token.tipo == 'ESCREVA':
            inicio = esperar('ESCREVA')
            esperar('ABRE_PAR', "'('")
            valor = expressao()
            esperar('FECHA_PAR', "')'")
            esperar('PONTO_VIRGULA', "';'")
            return No('escreva', [valor], linha=inicio.linha, coluna=inicio.coluna)
        if token.tipo == 'RETORNE':
            inicio = esperar('RETORNE')
            filhos = [] if atual().tipo == 'PONTO_VIRGULA' else [expressao()]
            esperar('PONTO_VIRGULA', "';'")
            return No('retorne', filhos, linha=inicio.linha, coluna=inicio.coluna)
        raise ErroMPL('sintatico', token.linha, token.coluna,
                      'esperava um comando')

    def funcao():
        inicio = esperar('FUNCAO')
        retorno, _ = tipo()
        nome = esperar('ID', 'o nome da funcao')
        esperar('ABRE_PAR', "'('")
        parametros = []
        if atual().tipo != 'FECHA_PAR':
            while True:
                tipo_parametro, token_tipo = tipo(permite_vazio=False)
                parametro = esperar('ID', 'o nome do parametro')
                parametros.append(No(f'parametro {parametro.lexema} {tipo_parametro}',
                                     linha=token_tipo.linha, coluna=token_tipo.coluna,
                                     nome=parametro.lexema, tipo=tipo_parametro))
                if not aceitar('VIRGULA'):
                    break
        esperar('FECHA_PAR', "')'")
        params = No('parametros', parametros, linha=nome.linha, coluna=nome.coluna)
        corpo = bloco()
        return No(f'funcao {nome.lexema} {retorno}', [params, corpo],
                  linha=inicio.linha, coluna=inicio.coluna,
                  nome=nome.lexema, tipo=retorno)

    funcoes = []
    while atual().tipo != 'FIM_ARQUIVO':
        funcoes.append(funcao())
    fim = esperar('FIM_ARQUIVO')
    return No('programa', funcoes, linha=1 if funcoes else fim.linha,
              coluna=1 if funcoes else fim.coluna)


def despejar(no, nivel=0, saida=None):
    """Imprime a arvore no formato do --ast. Ja esta pronto: dois espacos por nivel."""
    saida = saida if saida is not None else []
    saida.append('  ' * nivel + no.rotulo)
    for f in no.filhos:
        despejar(f, nivel + 1, saida)
    return saida
