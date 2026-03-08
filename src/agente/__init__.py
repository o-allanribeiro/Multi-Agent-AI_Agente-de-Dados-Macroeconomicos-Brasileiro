# -*- coding: utf-8 -*-
"""
Pacote agente — Núcleo do Agente LangGraph.

Exporta a factory principal e o estado do agente.
"""
from agente.agent import create_agent
from agente.state import AgentState

__all__ = ["create_agent", "AgentState"]
