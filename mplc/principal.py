"""Linha de comando do compilador e da máquina virtual."""
import sys
from pathlib import Path

from mplc.erros import ErroMPL
from mplc import lexico, sintatico, semantica, intermediario, gerador, vm

MODOS = {'--tokens': 'tokens', '--ast': 'ast', '--tabela': 'tabela', '--ir': 'ir'}


def compilar_ate(fonte, ate):
    """Roda as fases ate a pedida e devolve as linhas para imprimir."""
    tokens = lexico.analisar(fonte)
    if ate == 'tokens':
        return [str(t) for t in tokens]

    arvore = sintatico.analisar(tokens)
    if ate == 'ast':
        return sintatico.despejar(arvore)

    try:
        tabela = semantica.analisar(arvore)
        if ate == 'tabela':
            return semantica.despejar(tabela)

        codigo = intermediario.gerar(arvore, tabela)
        if ate == 'ir':
            return intermediario.despejar(codigo)

        return gerador.gerar(codigo)
    except RecursionError:
        raise ErroMPL('semantico', arvore.linha, arvore.coluna,
                      'programa excede o limite de profundidade da compilacao') from None


def normalizar_quebras(texto):
    return texto.replace('\r\n', '\n').replace('\r', '\n')


def ler_utf8(caminho, fase):
    dados = Path(caminho).read_bytes()
    try:
        return normalizar_quebras(dados.decode('utf-8'))
    except UnicodeDecodeError as erro:
        prefixo = normalizar_quebras(dados[:erro.start].decode('utf-8'))
        linha = prefixo.count('\n') + 1
        coluna = len(prefixo.rsplit('\n', 1)[-1]) + 1
        raise ErroMPL(fase, linha, coluna, 'sequencia UTF-8 invalida') from None

def main(argv):
    ate, rodar, arquivos = 'bytecode', False, []
    for a in argv:
        if a in MODOS:
            ate = MODOS[a]
        elif a == '--rodar':
            rodar = True
        else:
            arquivos.append(a)

    if len(arquivos) != 1:
        print('uso: ./compilar [--tokens|--ast|--tabela|--ir] programa.mpl', file=sys.stderr)
        print('     ./executar programa.mplb', file=sys.stderr)
        return 1

    caminho = arquivos[0]
    try:
        if rodar:
            vm.executar(ler_utf8(caminho, 'execucao'), sys.stdout)
            return 0

        fonte = ler_utf8(caminho, 'lexico')
        linhas = compilar_ate(fonte, ate)

        if ate == 'bytecode':
            destino = caminho[:-4] + '.mplb' if caminho.endswith('.mpl') else caminho + '.mplb'
            with open(destino, 'w', encoding='utf-8') as f:
                f.write('\n'.join(linhas) + '\n')
        else:
            print('\n'.join(linhas))
        return 0

    except ErroMPL as e:
        print(e, file=sys.stderr)
        return 2 if e.fase == 'execucao' else 1
    except OSError as e:
        print(f'{e.filename or caminho}: {e.strerror}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.exit(main(sys.argv[1:]))
