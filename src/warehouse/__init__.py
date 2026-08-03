# -*- coding: utf-8 -*-
"""
warehouse — Data warehouse histórico incremental (DuckDB + Parquet).

Diferente de `tools/cache.py` (cache por combinação exata de parâmetros de
busca — janela pedida por cada pergunta), este pacote mantém o **histórico
completo** de cada série macroeconômica, atualizado incrementalmente.

Isso resolve duas coisas ao mesmo tempo:
  1. Reduz chamadas às APIs externas (BCB/IBGE/IPEA/Banco Mundial) — o
     backfill roda uma vez, atualizações seguintes buscam só o delta.
  2. Corrige uma inconsistência real: `agente/nodes/stats.py` calculava
     z-score/percentil sobre a mesma janela que o Planner buscou para exibir
     no gráfico (2, 3, 5 ou 10 anos, dependendo da pergunta) — o mesmo valor
     atual podia cair em percentis bem diferentes dependendo de como a
     pergunta foi formulada. Com o warehouse, esses cálculos sempre usam o
     histórico completo salvo, independente da janela de exibição.

Módulos:
  - registry.py: manifesto único de séries fetcháveis + resolução de coluna → series_id
  - store.py:    leitura/escrita do histórico (Parquet) e metadados (DuckDB)
  - pipeline.py: lógica de atualização incremental por fonte
"""
