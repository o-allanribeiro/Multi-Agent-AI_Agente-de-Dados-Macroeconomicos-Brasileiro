# Juros Externos (Estados Unidos) — Referência Macroeconômica

## Definição

Os **juros externos** são as taxas de juros das economias centrais que servem de referência
para o custo de capital global. Para o Brasil, a referência é a curva de juros dos títulos do
Tesouro americano (*Treasuries*), tratada como a taxa livre de risco internacional.

Este agente usa séries do FRED (Federal Reserve Bank of St. Louis), em **% a.a., média mensal**:

| Série | O que mede |
|---|---|
| TB3MS | Treasury Bill de 3 meses (mercado secundário) — juro de curto prazo, próximo à política monetária do Fed |
| GS1 | Título do Tesouro de 1 ano (prazo constante) |
| GS2 | Título do Tesouro de 2 anos (prazo constante) |
| GS5 | Título do Tesouro de 5 anos (prazo constante) |
| GS10 | Título do Tesouro de 10 anos (prazo constante) — referência de juro longo |

---

## Inclinação da Curva (indicador derivado)

```
inclinacao_curva_eua = GS10 - TB3MS      (em pontos percentuais)
```

| Situação | Interpretação |
|---|---|
| Inclinação positiva | Curva **normal**: juros longos acima dos curtos |
| Inclinação próxima de zero | Curva **achatada**: mercado precifica juros mais baixos adiante ou menor prêmio de prazo |
| Inclinação negativa | Curva **invertida**: juros curtos acima dos longos; historicamente tratada como sinal de alerta para a atividade americana |

A inclinação é um **indicador de contexto**, não uma previsão: a relação com recessões é
empírica e não implica causalidade.

---

## Canais de Transmissão para o Brasil

- **Fluxo de capitais e carry trade**: juros americanos mais altos reduzem o diferencial de
  juros em relação à Selic e tendem a diminuir o apetite por ativos de países emergentes.
- **Câmbio**: movimentos de alta dos juros externos tendem a pressionar o Real (depreciação).
- **Risco-país e custo de financiamento externo**: juros longos dos EUA entram no custo da
  dívida externa de empresas e do governo.
- **Mercado acionário**: juros externos mais altos elevam a taxa de desconto aplicada a ativos
  de risco, o que é um dos canais discutidos na literatura sobre determinantes do Ibovespa.
- **Política monetária doméstica**: o Banco Central do Brasil acompanha o ciclo do Fed ao
  calibrar a Selic, especialmente por seus efeitos sobre câmbio e expectativas.

---

## Cuidados de Interpretação

1. **Níveis vs. variações**: séries de juros são persistentes; correlações entre níveis podem
   ser espúrias. Compare variações ou use métodos próprios para séries não estacionárias.
2. **Defasagens**: os efeitos sobre câmbio e bolsa podem ser contemporâneos ou defasados.
3. **Frequência**: as séries do FRED usadas aqui são mensais (média do mês); não capturam
   movimentos intramensais.
4. **Moedas e unidades diferentes**: comparar Selic (% a.a. nominal em reais) com Treasuries
   (% a.a. nominal em dólares) exige considerar inflação e expectativa de câmbio.

---

## Fontes de Dados

| Indicador | Fonte | Série |
|---|---|---|
| Treasury Bill 3 meses | FRED (Federal Reserve Bank of St. Louis) | TB3MS |
| Treasury 1 / 2 / 5 / 10 anos | FRED (Federal Reserve Bank of St. Louis) | GS1 / GS2 / GS5 / GS10 |

This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.
