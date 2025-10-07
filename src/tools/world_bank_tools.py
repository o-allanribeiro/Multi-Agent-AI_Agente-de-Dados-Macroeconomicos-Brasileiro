# -*- coding: utf-8 -*-
"""
Módulo de Ferramentas para Coleta de Dados do Banco Mundial.

Este script contém funções para interagir com a API de Indicadores do
Banco Mundial, focando em dados sociais e de desenvolvimento que são
relevantes para a análise de vulnerabilidade estrutural.
"""

import pandas as pd
import wbgapi as wb

# --- Mapeamento de Séries do Banco Mundial ---
# Centraliza os códigos de séries importantes para facilitar a manutenção.
WB_SERIES_MAP = {
    "gini": "SI.POV.GINI",  # Índice de Gini
}

def get_gini_series(country_code: str = "BRA"):
    """
    Busca a série histórica do Coeficiente de Gini para um país.

    Args:
        country_code (str): O código ISO alpha-3 do país. Padrão é "BRA".

    Returns:
        pd.DataFrame: DataFrame com as colunas 'Date' e o valor da série,
                      ou None se ocorrer um erro.
    """
    series_id = WB_SERIES_MAP["gini"]
    print(f"--- TOOL: Buscando série {series_id} para o país {country_code} do Banco Mundial ---")
    
    try:
        # Busca os dados usando a biblioteca wbgapi
        # A biblioteca retorna os dados em um formato "wide"
        df_wide = wb.data.DataFrame(series_id, economy=country_code, time=range(1980, 2024))
        
        # --- Processamento e Limpeza ---
        # A API retorna anos como colunas (ex: 'YR1981', 'YR1982').
        # Precisamos transformar (melt) o DataFrame para o formato "long",
        # com uma coluna para data e outra para o valor.
        df_long = df_wide.reset_index().melt(
            id_vars=['economy'], 
            var_name='Year', 
            value_name=series_id
        )
        
        # Limpa o nome da coluna de ano (remove 'YR') e converte para data
        df_long['Date'] = pd.to_datetime(df_long['Year'].str.replace('YR', ''), format='%Y')
        
        # Renomeia e seleciona as colunas finais
        df_final = df_long[['Date', series_id]].dropna().set_index('Date')
        
        print(f"--- TOOL: Dados da série {series_id} obtidos com sucesso. {len(df_final)} registros encontrados. ---")
        return df_final

    except Exception as e:
        print(f"--- TOOL ERROR: Ocorreu um erro inesperado ao buscar a série {series_id}. ---")
        print(f"Detalhes do erro: {e}")
        return None

# --- Bloco de Teste ---
if __name__ == '__main__':
    print(">>> INICIANDO TESTE 1: Coeficiente de Gini")
    gini_df = get_gini_series()
    if gini_df is not None:
        print("\n--- Resultado do Teste (Gini - SI.POV.GINI): ---")
        print(gini_df.tail()) # Mostra os últimos 5 registros
    print("<<< FIM DO TESTE 1: Coeficiente de Gini")

