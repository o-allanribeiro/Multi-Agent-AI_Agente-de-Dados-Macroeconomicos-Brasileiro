# -*- coding: utf-8 -*-
"""Dados e mocks reutilizáveis nos testes."""
import pandas as pd

# Mock de resposta HTTP IPEADATA (formato OData)
MOCK_IPEA_RESPONSE = {
    "value": [
        {"VALDATA": "2020-01-01T00:00:00", "VALVALOR": 98.5},
        {"VALDATA": "2020-04-01T00:00:00", "VALVALOR": 95.2},
        {"VALDATA": "2020-07-01T00:00:00", "VALVALOR": 97.8},
        {"VALDATA": "2020-10-01T00:00:00", "VALVALOR": 99.1},
        {"VALDATA": "2021-01-01T00:00:00", "VALVALOR": 102.3},
        {"VALDATA": "2021-04-01T00:00:00", "VALVALOR": 104.7},
    ]
}

# Mock de planner output do LLM (JSON esperado)
MOCK_PLANNER_OUTPUT_BCB = {
    "plan": "Buscar série IPCA dos últimos 2 anos via BCB.",
    "tool_to_use": "get_bcb_series",
    "tool_params": {"series_code": 433, "last_n_years": 2},
}

MOCK_PLANNER_OUTPUT_NONE = {
    "plan": "Pergunta fora do escopo das ferramentas disponíveis.",
    "tool_to_use": "none",
    "tool_params": None,
}

MOCK_PLANNER_OUTPUT_GINI = {
    "plan": "Buscar Coeficiente de Gini para o Brasil via Banco Mundial.",
    "tool_to_use": "get_gini_series",
    "tool_params": {"country_code": "BRA"},
}
