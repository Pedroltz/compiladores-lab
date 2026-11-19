// Relatório de uma prova de regularidade. Os tempos estão em segundos.
funcao real tempoCorrida(inteiro voltas, real tempoVolta, real penalidade) {
  real total = voltas * tempoVolta + penalidade;
  retorne total;
}

funcao texto classificacao(real tempo, real limite) {
  se (tempo <= limite) {
    retorne "classificado";
  } senao {
    retorne "fora do limite";
  }
}

funcao vazio principal() {
  inteiro voltas = 4;
  real limite = 250;
  real tempoVolta = 59.75;
  inteiro etapa = 1;
  enquanto (etapa <= 3) {
    real tempo = tempoCorrida(voltas, tempoVolta, (etapa - 1) * 2.5);
    escreva("Etapa");
    escreva(etapa);
    escreva(tempo);
    escreva(classificacao(tempo, limite));
    tempoVolta = tempoVolta + 1.25;
    etapa = etapa + 1;
  }

  // Converte a resolução do sensor de segundos para microssegundos.
  real resolucao = 0.0000004;
  escreva("Resolução do sensor em microssegundos");
  escreva(1000000 * resolucao);
}
