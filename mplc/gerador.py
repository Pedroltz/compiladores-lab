"""Traduz o código de três endereços para instruções de uma VM de pilha."""
import json


CABECALHO = 'MPLB 1'


def traduzir(instrucao):
    op, args = instrucao.op, instrucao.args
    if op == 'const':
        destino, valor = args
        return [('CONST', valor), ('GUARDE', destino)]
    if op == 'copia':
        destino, origem = args
        return [('CARREGUE', origem), ('GUARDE', destino)]
    if op == 'binario':
        destino, operador, esquerda, direita = args
        return [('CARREGUE', esquerda), ('CARREGUE', direita),
                ('BINARIO', operador), ('GUARDE', destino)]
    if op in {'unario', 'real'}:
        destino, *operacao, origem = args
        return [('CARREGUE', origem), (op.upper(), *operacao), ('GUARDE', destino)]
    if op == 'chamada':
        destino, nome, argumentos = args
        passos = [('CARREGUE', arg) for arg in argumentos]
        passos.append(('CHAME', nome, len(argumentos)))
        passos.append(('DESCARTE',) if destino is None else ('GUARDE', destino))
        return passos
    if op == 'se_falso':
        teste, rotulo = args
        return [('CARREGUE', teste), ('SE_FALSO', rotulo)]
    if op == 'desvie':
        return [('DESVIE', args[0])]
    if op == 'escreva':
        return [('CARREGUE', args[0]), ('ESCREVA',)]
    valor, = args
    if valor is None:
        return [('RETORNE', False)]
    return [('CARREGUE', valor), ('RETORNE', True)]


def gerar(codigo_intermediario):
    """Serializa uma função por seção e encoda os saltos como índices locais."""
    linhas = [CABECALHO]
    for funcao in codigo_intermediario:
        linhas.append(json.dumps(['FUNCAO', funcao.nome, funcao.parametros]))
        rotulos = {}
        instrucoes = []
        for instrucao in funcao.instrucoes:
            if instrucao.op == 'rotulo':
                rotulos[instrucao.args[0]] = len(instrucoes)
            else:
                for passo in traduzir(instrucao):
                    instrucoes.append([instrucao.linha, instrucao.coluna, *passo])

        for linha, coluna, op, *args in instrucoes:
            if op in {'DESVIE', 'SE_FALSO'}:
                args = [rotulos[args[0]]]
            registro = json.dumps([linha, coluna, op, *args], ensure_ascii=False)
            linhas.append(f'  {registro}')
    return linhas
