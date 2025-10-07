# -*- coding: utf-8 -*-
"""
Este módulo contém as funções (ferramentas) para interagir com o
Sistema Gerenciador de Séries Temporais (SGS) do Banco Central do Brasil (BCB),
utilizando a biblioteca python-bcb.

O propósito é servir como ferramenta de coleta de dados para o
"Agente de Pesquisa para Análise de Vulnerabilidade Estrutural".
"""

import pandas as pd
from datetime import datetime, date
from bcb import sgs

# --- Tabela de Mapeamento de Séries do BCB ---
# Este dicionário centraliza os códigos das séries, facilitando a manutenção
# e a legibilidade do código do agente.
BCB_SERIES_MAP = {
    "ipca": {
        "code": 433,
        "name": "IPCA (Índice Nacional de Preços ao Consumidor Amplo)",
        "description": "Variação percentual mensal do índice de inflação oficial do Brasil."
    },
    "selic": {
        "code": 432,
        "name": "Taxa Selic (Meta)",
        "description": "Meta da taxa básica de juros definida pelo COPOM, em % ao ano."
    },
    "taxa_desocupacao": {
        "code": 24369,
        "name": "Taxa de Desocupação (PNAD Contínua)",
        "description": "Percentual de pessoas desocupadas na força de trabalho, baseada na pesquisa do IBGE."
    },
    "dolar": {
        "code": 1,
        "name": "Taxa de Câmbio (Dólar PTAX - Venda)",
        "description": "Taxa de câmbio R$ / US$ (venda), cotações diárias."
    }
}

def get_bcb_series(series_code: int | str, start_date: str | None = None, last_n_years: int | None = None) -> pd.DataFrame | None:
    """
    Busca uma série temporal específica do SGS do Banco Central do Brasil.

    A função prioriza o argumento 'start_date'. Se 'start_date' não for fornecido,
    ela usará 'last_n_years' para calcular a data de início.

    Args:
        series_code (int | str): O código da série no sistema SGS.
        start_date (str | None): A data de início para a busca, no formato 'YYYY-MM-DD'.
        last_n_years (int | None): O número de anos para buscar a partir da data atual.

    Returns:
        pd.DataFrame | None: Um DataFrame do Pandas com a série temporal se a consulta
                             for bem-sucedida, caso contrário, retorna None.
    """
    if start_date is None and last_n_years is not None:
        today = date.today()
        start_date = today.replace(year=today.year - last_n_years).strftime('%Y-%m-%d')
    elif start_date is None and last_n_years is None:
        print("--- TOOL ERROR: É necessário fornecer 'start_date' ou 'last_n_years'. ---")
        return None

    print(f"---  TOOL: Buscando série {series_code} do BCB de {start_date} até hoje ---")

    try:
        # Utiliza a biblioteca 'python-bcb' para obter os dados.
        df = sgs.get({str(series_code): series_code}, start=start_date) # Garantir que a chave seja string

        if df.empty:
            print(f"--- TOOL WARNING: Nenhum dado encontrado para a série {series_code} no período solicitado. ---")
            return None

        print(f"--- TOOL: Dados da série {series_code} obtidos com sucesso. {len(df)} registros encontrados. ---")
        return df

    except Exception as e:
        print(f"--- TOOL ERROR: Ocorreu um erro ao buscar a série {series_code} do BCB. ---")
        print(f"Detalhes do erro: {e}")
        return None

# --- Bloco de Teste ---
# Este bloco só é executado quando o script é chamado diretamente.
# Permite testar a funcionalidade do módulo de forma isolada.
if __name__ == '__main__':
    print("Executando teste do módulo bcb_tools.py...")
    print("="*50)

    # Teste 1: Buscar a série do IPCA dos últimos 5 anos.
    print("\n>>> INICIANDO TESTE 1: IPCA")
    ipca_code = BCB_SERIES_MAP['ipca']['code']
    df_ipca = get_bcb_series(series_code=ipca_code, last_n_years=5)
    if df_ipca is not None:
        print(f"\n--- Resultado do Teste (IPCA - {ipca_code}): ---\n", df_ipca.tail())
    print("<<< FIM DO TESTE 1: IPCA")
    print("="*50)

    # Teste 2: Buscar a série da SELIC dos últimos 10 anos.
    print("\n>>> INICIANDO TESTE 2: Selic")
    selic_code = BCB_SERIES_MAP['selic']['code']
    df_selic = get_bcb_series(series_code=selic_code, last_n_years=10)
    if df_selic is not None:
        print(f"\n--- Resultado do Teste (Selic - {selic_code}): ---\n", df_selic.tail())
    print("<<< FIM DO TESTE 2: Selic")
    print("="*50)

    # Teste 3: Buscar a série da Taxa de Desocupação desde o início da série.
    print("\n>>> INICIANDO TESTE 3: Desocupação")
    desocup_code = BCB_SERIES_MAP['taxa_desocupacao']['code']
    df_desocup = get_bcb_series(series_code=desocup_code, start_date='2012-03-01') # Início da série histórica
    if df_desocup is not None:
        print(f"\n--- Resultado do Teste (Desocupação - {desocup_code}): ---\n", df_desocup.tail())
    print("<<< FIM DO TESTE 3: Desocupação")
    print("="*50)

    # Teste 4: Buscar a série do Dólar dos últimos 2 anos.
    print("\n>>> INICIANDO TESTE 4: Dólar")
    dolar_code = BCB_SERIES_MAP['dolar']['code']
    df_dolar = get_bcb_series(series_code=dolar_code, last_n_years=2)
    if df_dolar is not None:
        print(f"\n--- Resultado do Teste (Dólar - {dolar_code}): ---\n", df_dolar.tail())
    print("<<< FIM DO TESTE 4: Dólar")
    print("="*50)

