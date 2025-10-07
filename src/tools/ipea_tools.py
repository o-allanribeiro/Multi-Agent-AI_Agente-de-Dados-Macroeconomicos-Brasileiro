# -*- coding: utf-8 -*-
"""
Módulo para as ferramentas de interação com a API do IPEADATA.

Este módulo contém funções para buscar séries temporais econômicas e sociais
diretamente da API pública do IPEADATA, com foco em variáveis relevantes
para a análise de vulnerabilidade estrutural da economia brasileira.
"""

import pandas as pd
import requests

# URL base da API do IPEADATA, conforme a documentação oficial.
BASE_URL = "https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{series_code}')"

# Mapeamento de séries do IPEADATA relevantes para o TCC
# A série do Gini ('SOCIAL_GINI') foi removida pois está inativa na fonte.
IPEA_SERIES_MAP = {
    "fbcf": {
        "code": "GAC12_INDFBCF12", # Código correto identificado na pesquisa
        "name": "Formação Bruta de Capital Fixo (FBCF)",
        "description": "Indicador IPEA de FBCF - índice real dessazonalizado (média 1995 = 100). Fonte: IPEADATA."
    },
}

def get_ipea_series(series_code: str) -> pd.DataFrame | None:
    """
    Busca uma série temporal da API do IPEADATA e a retorna como um DataFrame.

    Args:
        series_code (str): O código da série a ser buscada (ex: 'GAC12_INDFBCF12').

    Returns:
        pd.DataFrame | None: Um DataFrame com a série temporal (índice de data e
                             uma coluna com o valor) ou None se ocorrer um erro.
    """
    print(f"--- TOOL: Buscando série {series_code} do IPEADATA ---")
    
    url = BASE_URL.format(series_code=series_code)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not data or 'value' not in data or not data['value']:
            print(f"--- TOOL WARNING: Nenhum dado encontrado para a série {series_code}. ---")
            return None

        df = pd.DataFrame(data['value'])
        df = df[['VALDATA', 'VALVALOR']]
        df = df.rename(columns={'VALDATA': 'Date', 'VALVALOR': series_code})

        # --- CORREÇÃO APLICADA ---
        # Converte para datetime, transformando erros de parsing em NaT (Not a Time)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        # Remove linhas onde a data não pôde ser convertida
        df = df.dropna(subset=['Date'])
        
        df = df.set_index('Date')
        
        print(f"--- TOOL: Dados da série {series_code} obtidos com sucesso. {len(df)} registros encontrados. ---")
        return df

    except requests.exceptions.RequestException as e:
        print(f"--- TOOL ERROR: Ocorreu um erro de conexão ao buscar a série {series_code} do IPEA. ---")
        print(f"Detalhes do erro: {e}")
        return None
    except Exception as e:
        print(f"--- TOOL ERROR: Ocorreu um erro inesperado ao processar a série {series_code}. ---")
        print(f"Detalhes do erro: {e}")
        return None

# --- Bloco de Teste ---
if __name__ == '__main__':
    print("Executando teste do módulo ipea_tools.py...")
    print("="*60)

    # Teste 1: Buscar a Formação Bruta de Capital Fixo (FBCF)
    print("\n>>> INICIANDO TESTE 1: FBCF")
    fbcf_code = IPEA_SERIES_MAP['fbcf']['code']
    fbcf_data = get_ipea_series(fbcf_code)
    if fbcf_data is not None:
        print(f"\n--- Resultado do Teste (FBCF - {fbcf_code}): ---")
        print(fbcf_data.head()) # Mostra os primeiros 5 registros
        print("...")
        print(fbcf_data.tail()) # Mostra os últimos 5 registros
    print("<<< FIM DO TESTE 1: FBCF")
    print("="*60)

