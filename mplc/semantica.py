"""Resolve nomes e tipos e verifica o retorno das funções."""
from dataclasses import dataclass, field

from mplc.erros import ErroMPL


NUMERICOS = {'inteiro', 'real'}


@dataclass
class Simbolo:
    nome: str
    categoria: str
    tipo: str
    linha: int
    local: str = ''
    parametros: tuple[str, ...] = ()


@dataclass
class Escopo:
    numero: int
    descricao: str
    pai: 'Escopo | None' = None
    simbolos: dict[str, Simbolo] = field(default_factory=dict)


def erro(no, mensagem):
    raise ErroMPL('semantico', no.linha, no.coluna, mensagem)


def exigir_tipo(no, obtido, esperado):
    if obtido == esperado:
        return
    if obtido == 'inteiro' and esperado == 'real':
        no.extra['promover'] = True
        return
    erro(no, f'esperava {esperado}, encontrei {obtido}')


class Analisador:
    def __init__(self):
        self.global_ = Escopo(0, 'global')
        self.escopos = [self.global_]

    def abrir(self, descricao, pai):
        escopo = Escopo(len(self.escopos), descricao, pai)
        self.escopos.append(escopo)
        return escopo

    def declarar(self, no, escopo, categoria, parametros=()):
        nome, tipo = no.extra['nome'], no.extra['tipo']
        if nome in escopo.simbolos:
            erro(no, f'{nome!r} ja foi declarado neste escopo')
        local = f'v{escopo.numero}_{len(escopo.simbolos)}' if escopo.pai else ''
        simbolo = Simbolo(nome, categoria, tipo, no.linha, local, parametros)
        escopo.simbolos[nome] = simbolo
        no.extra['simbolo'] = simbolo
        return simbolo

    def variavel(self, no, escopo):
        nome = no.extra['nome']
        while escopo.pai is not None:
            if nome in escopo.simbolos:
                simbolo = escopo.simbolos[nome]
                no.extra['simbolo'] = simbolo
                return simbolo
            escopo = escopo.pai
        erro(no, f'variavel {nome!r} nao declarada')

    def chamada(self, no, escopo, como_comando=False):
        nome = no.extra['nome']
        funcao = self.global_.simbolos.get(nome)
        if funcao is None:
            erro(no, f'funcao {nome!r} nao declarada')
        if funcao.tipo == 'vazio' and not como_comando:
            erro(no, f'funcao {nome!r} nao produz valor')
        if len(no.filhos) != len(funcao.parametros):
            erro(no, f'{nome!r} espera {len(funcao.parametros)} argumento(s), '
                     f'recebeu {len(no.filhos)}')
        for argumento, esperado in zip(no.filhos, funcao.parametros):
            exigir_tipo(argumento, self.expressao(argumento, escopo), esperado)
        no.extra['simbolo'] = funcao
        return funcao.tipo

    def binario(self, no, escopo):
        esquerda, direita = no.filhos
        a = self.expressao(esquerda, escopo)
        b = self.expressao(direita, escopo)
        op = no.extra['op']
        if op in {'e', 'ou'} and a == b == 'logico':
            return 'logico'
        if op == '%' and a == b == 'inteiro':
            return 'inteiro'
        if op == '+' and a == b == 'texto':
            return 'texto'
        if op in {'==', '!='} and a == b:
            return 'logico'
        if op in {'+', '-', '*', '/', '<', '<=', '>', '>=', '==', '!='}:
            if a in NUMERICOS and b in NUMERICOS:
                comum = 'real' if 'real' in (a, b) else 'inteiro'
                exigir_tipo(esquerda, a, comum)
                exigir_tipo(direita, b, comum)
                return comum if op in {'+', '-', '*', '/'} else 'logico'
        erro(no, f'operador {op!r} nao aceita {a} e {b}')

    def expressao(self, no, escopo):
        classe = no.rotulo.split(' ', 1)[0]
        if classe == 'literal':
            return no.extra['tipo']
        if classe == 'variavel':
            return self.variavel(no, escopo).tipo
        if classe == 'chamada':
            return self.chamada(no, escopo)
        if classe == 'binario':
            return self.binario(no, escopo)

        operando, = no.filhos
        tipo = self.expressao(operando, escopo)
        op = no.extra['op']
        if (op == 'nao' and tipo == 'logico') or (op == '-' and tipo in NUMERICOS):
            return tipo
        erro(no, f'operador {op!r} nao aceita {tipo}')

    def bloco(self, no, pai, retorno):
        escopo = self.abrir('bloco', pai)
        garante_retorno = False
        for comando in no.filhos:
            # Mesmo código inalcançável precisa respeitar as regras de tipos.
            if self.comando(comando, escopo, retorno):
                garante_retorno = True
        return garante_retorno

    def comando(self, no, escopo, retorno):
        classe = no.rotulo.split(' ', 1)[0]
        if classe == 'bloco':
            return self.bloco(no, escopo, retorno)
        if classe == 'declaracao':
            # O inicializador é verificado no ambiente anterior à declaração.
            if no.filhos:
                valor, = no.filhos
                exigir_tipo(valor, self.expressao(valor, escopo), no.extra['tipo'])
            self.declarar(no, escopo, 'variavel')
        elif classe == 'atribuicao':
            simbolo = self.variavel(no, escopo)
            valor, = no.filhos
            exigir_tipo(valor, self.expressao(valor, escopo), simbolo.tipo)
        elif classe in {'se', 'enquanto'}:
            condicao, *blocos = no.filhos
            exigir_tipo(condicao, self.expressao(condicao, escopo), 'logico')
            retornos = [self.bloco(bloco, escopo, retorno) for bloco in blocos]
            return len(retornos) == 2 and all(retornos)
        elif classe == 'retorne':
            if retorno == 'vazio' and no.filhos:
                erro(no, 'funcao vazio requer retorne sem valor')
            if retorno != 'vazio':
                if not no.filhos:
                    erro(no, f'retorne exige um valor do tipo {retorno}')
                valor, = no.filhos
                exigir_tipo(valor, self.expressao(valor, escopo), retorno)
            return True
        elif classe == 'escreva':
            self.expressao(no.filhos[0], escopo)
        elif classe == 'chamada':
            self.chamada(no, escopo, como_comando=True)
        return False

    def analisar(self, arvore):
        principal = None
        for no in arvore.filhos:
            parametros = tuple(p.extra['tipo'] for p in no.filhos[0].filhos)
            funcao = self.declarar(no, self.global_, 'funcao', parametros)
            if funcao.nome == 'principal':
                principal = no
                if funcao.parametros or funcao.tipo != 'vazio':
                    erro(no, 'principal precisa ser vazio e nao receber parametros')
        if principal is None:
            raise ErroMPL('semantico', 1, 1, 'falta a funcao principal')

        for no in arvore.filhos:
            funcao = no.extra['simbolo']
            parametros, corpo = no.filhos
            escopo = self.abrir(f'funcao {funcao.nome}', self.global_)
            for parametro in parametros.filhos:
                self.declarar(parametro, escopo, 'parametro')
            if not self.bloco(corpo, escopo, funcao.tipo) and funcao.tipo != 'vazio':
                erro(no, f'nem todos os caminhos de {funcao.nome!r} retornam um valor')
        return self.escopos


def analisar(arvore):
    return Analisador().analisar(arvore)


def despejar(tabela):
    linhas = []
    for escopo in tabela:
        cabecalho = f'escopo {escopo.numero} {escopo.descricao}'
        if escopo.pai is not None:
            cabecalho += f' pai {escopo.pai.numero}'
        linhas.append(cabecalho)
        for simbolo in escopo.simbolos.values():
            tipo = simbolo.tipo
            if simbolo.categoria == 'funcao':
                tipo += f'({",".join(simbolo.parametros)})'
            linhas.append(f'  {simbolo.nome}|{simbolo.categoria}|{tipo}|{simbolo.linha}')
    return linhas
