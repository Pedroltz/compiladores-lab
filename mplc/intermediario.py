"""Gera código de três endereços a partir da árvore anotada."""
import json
from dataclasses import dataclass, field


PADRAO = {'inteiro': 0, 'real': 0.0, 'logico': False, 'texto': ''}
LEITOR_LITERAL = {
    'inteiro': int,
    'real': float,
    'logico': lambda lexema: lexema == 'verdadeiro',
    'texto': lambda lexema: json.loads(lexema, strict=False),
}


@dataclass
class Instrucao:
    op: str
    args: tuple
    linha: int
    coluna: int


@dataclass
class Funcao:
    nome: str
    tipo: str
    parametros: list[str]
    instrucoes: list[Instrucao] = field(default_factory=list)


class Tradutor:
    def __init__(self, funcao):
        self.funcao = funcao
        self.temporarios = 0
        self.rotulos = 0

    def temporario(self):
        nome = f't{self.temporarios}'
        self.temporarios += 1
        return nome

    def rotulo(self):
        nome = f'L{self.rotulos}'
        self.rotulos += 1
        return nome

    def emitir(self, comando, op, *args):
        self.funcao.instrucoes.append(Instrucao(op, args, comando.linha, comando.coluna))

    def chamada(self, no, comando, descartar=False):
        argumentos = [self.expressao(arg, comando) for arg in no.filhos]
        nome = no.extra['simbolo'].nome
        destino = None if descartar else self.temporario()
        self.emitir(comando, 'chamada', destino, nome, argumentos)
        return destino

    def expressao(self, no, comando):
        classe = no.rotulo.split(' ', 1)[0]
        if classe == 'variavel':
            local = no.extra['simbolo'].local
        elif classe == 'chamada':
            local = self.chamada(no, comando)
        elif classe == 'literal':
            local = self.temporario()
            leitor = LEITOR_LITERAL[no.extra['tipo']]
            self.emitir(comando, 'const', local, leitor(no.extra['valor']))
        else:
            operandos = [self.expressao(filho, comando) for filho in no.filhos]
            local = self.temporario()
            self.emitir(comando, classe, local, no.extra['op'], *operandos)
        if no.extra.get('promover'):
            real = self.temporario()
            self.emitir(comando, 'real', real, local)
            return real
        return local

    def bloco(self, no):
        for comando in no.filhos:
            self.comando(comando)

    def comando(self, no):
        classe = no.rotulo.split(' ', 1)[0]
        if classe == 'bloco':
            self.bloco(no)
        elif classe in {'declaracao', 'atribuicao'}:
            simbolo = no.extra['simbolo']
            if no.filhos:
                valor = self.expressao(no.filhos[0], no)
                self.emitir(no, 'copia', simbolo.local, valor)
            else:
                self.emitir(no, 'const', simbolo.local, PADRAO[simbolo.tipo])
        elif classe == 'se':
            condicao, entao, *senao = no.filhos
            outro = self.rotulo()
            teste = self.expressao(condicao, no)
            self.emitir(no, 'se_falso', teste, outro)
            self.bloco(entao)
            if senao:
                fim = self.rotulo()
                self.emitir(no, 'desvie', fim)
                self.emitir(no, 'rotulo', outro)
                self.bloco(senao[0])
                self.emitir(no, 'rotulo', fim)
            else:
                self.emitir(no, 'rotulo', outro)
        elif classe == 'enquanto':
            condicao, corpo = no.filhos
            inicio, fim = self.rotulo(), self.rotulo()
            self.emitir(no, 'rotulo', inicio)
            teste = self.expressao(condicao, no)
            self.emitir(no, 'se_falso', teste, fim)
            self.bloco(corpo)
            self.emitir(no, 'desvie', inicio)
            self.emitir(no, 'rotulo', fim)
        elif classe == 'escreva':
            self.emitir(no, 'escreva', self.expressao(no.filhos[0], no))
        elif classe == 'retorne':
            valor = self.expressao(no.filhos[0], no) if no.filhos else None
            self.emitir(no, 'retorne', valor)
        elif classe == 'chamada':
            self.chamada(no, no, descartar=True)


def gerar(arvore, tabela):
    """Usa os vínculos da tabela registrados nos nós pela análise semântica."""
    codigo = []
    for no in arvore.filhos:
        simbolo = tabela[0].simbolos[no.extra['nome']]
        parametros, corpo = no.filhos
        locais = [param.extra['simbolo'].local for param in parametros.filhos]
        funcao = Funcao(simbolo.nome, simbolo.tipo, locais)
        tradutor = Tradutor(funcao)
        tradutor.bloco(corpo)
        if simbolo.tipo == 'vazio':
            tradutor.emitir(corpo, 'retorne', None)
        codigo.append(funcao)
    return codigo


def representar_literal(valor):
    if isinstance(valor, bool):
        return 'verdadeiro' if valor else 'falso'
    return json.dumps(valor, ensure_ascii=False)


def despejar(codigo):
    linhas = []
    for funcao in codigo:
        linhas.append(f'funcao {funcao.nome} {funcao.tipo} ({", ".join(funcao.parametros)})')
        for instrucao in funcao.instrucoes:
            op, args = instrucao.op, instrucao.args
            if op == 'rotulo':
                linhas.append(f'{args[0]}:')
                continue
            if op == 'const':
                texto = f'{args[0]} = {representar_literal(args[1])}'
            elif op == 'copia':
                texto = f'{args[0]} = {args[1]}'
            elif op == 'binario':
                destino, operador, esquerda, direita = args
                texto = f'{destino} = {esquerda} {operador} {direita}'
            elif op == 'unario':
                destino, operador, operando = args
                texto = f'{destino} = {operador} {operando}'
            elif op == 'real':
                texto = f'{args[0]} = real {args[1]}'
            elif op == 'chamada':
                destino, nome, argumentos = args
                texto = f'chama {nome}({", ".join(argumentos)})'
                if destino is not None:
                    texto = f'{destino} = {texto}'
            elif op == 'se_falso':
                texto = f'seFalso {args[0]} desvie {args[1]}'
            elif op == 'retorne' and args[0] is None:
                texto = 'retorne'
            else:
                texto = f'{op} {args[0]}'
            linhas.append(f'  {texto}')
        linhas.append('fim')
    return linhas
