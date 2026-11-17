"""Executa .mplb com uma pilha de operandos por registro de ativação."""
import json
import operator
from dataclasses import dataclass, field

from mplc.erros import ErroMPL
from mplc.gerador import CABECALHO


LIMITE_CHAMADAS = 1024


def quociente_inteiro(a, b):
    magnitude = abs(a) // abs(b)
    return -magnitude if (a < 0) != (b < 0) else magnitude


def dividir(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return quociente_inteiro(a, b)
    return a / b


def resto(a, b):
    return a - quociente_inteiro(a, b) * b


BINARIOS = {
    '+': operator.add, '-': operator.sub, '*': operator.mul, '/': dividir,
    '%': resto, '==': operator.eq, '!=': operator.ne, '<': operator.lt,
    '<=': operator.le, '>': operator.gt, '>=': operator.ge,
    'e': operator.and_, 'ou': operator.or_,
}
UNARIOS = {'-': operator.neg, 'nao': operator.not_}


@dataclass
class Funcao:
    parametros: list[str]
    instrucoes: list[list] = field(default_factory=list)


@dataclass
class Ativacao:
    funcao: Funcao
    locais: dict = field(default_factory=dict)
    operandos: list = field(default_factory=list)
    pc: int = 0


def ler(texto):
    cabecalho, _, corpo = texto.partition('\n')
    if cabecalho != CABECALHO:
        raise ValueError('cabecalho MPLB invalido')
    funcoes = {}
    funcao = None
    for linha in corpo.split('\n'):
        if not linha.strip():
            continue
        registro = json.loads(linha)
        if registro[0] == 'FUNCAO':
            _, nome, parametros = registro
            if nome in funcoes:
                raise ValueError('funcao duplicada')
            funcao = Funcao(parametros)
            funcoes[nome] = funcao
        else:
            if funcao is None:
                raise ValueError('instrucao fora de funcao')
            funcao.instrucoes.append(registro)
    return funcoes


def formatar(valor):
    if isinstance(valor, bool):
        return 'verdadeiro' if valor else 'falso'
    if isinstance(valor, float):
        return f'{valor:.6f}'
    return str(valor)


def executar(texto_mplb, saida):
    linha, coluna = 1, 1
    try:
        funcoes = ler(texto_mplb)
        chamadas = [Ativacao(funcoes['principal'])]
        while chamadas:
            atual = chamadas[-1]
            linha, coluna, op, *args = atual.funcao.instrucoes[atual.pc]
            atual.pc += 1
            pilha = atual.operandos
            if op == 'CONST':
                pilha.append(args[0])
            elif op == 'CARREGUE':
                pilha.append(atual.locais[args[0]])
            elif op == 'GUARDE':
                atual.locais[args[0]] = pilha.pop()
            elif op == 'BINARIO':
                direita = pilha.pop()
                esquerda = pilha.pop()
                pilha.append(BINARIOS[args[0]](esquerda, direita))
            elif op == 'UNARIO':
                pilha.append(UNARIOS[args[0]](pilha.pop()))
            elif op == 'REAL':
                pilha.append(float(pilha.pop()))
            elif op == 'DESVIE':
                atual.pc = args[0]
            elif op == 'SE_FALSO':
                if not pilha.pop():
                    atual.pc = args[0]
            elif op == 'CHAME':
                if len(chamadas) >= LIMITE_CHAMADAS:
                    raise ErroMPL('execucao', linha, coluna, 'estouro de pilha')
                nome, quantidade = args
                funcao = funcoes[nome]
                inicio = len(pilha) - quantidade
                valores = pilha[inicio:]
                del pilha[inicio:]
                locais = dict(zip(funcao.parametros, valores))
                chamadas.append(Ativacao(funcao, locais))
            elif op == 'RETORNE':
                valor = pilha.pop() if args[0] else None
                chamadas.pop()
                if chamadas:
                    chamadas[-1].operandos.append(valor)
            elif op == 'ESCREVA':
                saida.write(formatar(pilha.pop()) + '\n')
            elif op == 'DESCARTE':
                pilha.pop()
            else:
                raise ValueError(f'instrucao desconhecida: {op}')
    except ZeroDivisionError:
        raise ErroMPL('execucao', linha, coluna, 'divisao ou resto por zero') from None
    except OverflowError:
        raise ErroMPL('execucao', linha, coluna, 'valor numerico fora do intervalo') from None
    except (IndexError, KeyError, RecursionError, TypeError, ValueError):
        raise ErroMPL('execucao', linha, coluna, 'arquivo MPLB invalido') from None
