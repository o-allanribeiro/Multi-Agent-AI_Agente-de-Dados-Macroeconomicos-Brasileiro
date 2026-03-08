# -*- coding: utf-8 -*-
"""
CLI — Interface de Linha de Comando — Agente Macro-BR.

Interface interativa para consultas ao agente via terminal.
Útil para desenvolvimento, debug e demonstrações rápidas.

Execução:
    # Linux / macOS / Git Bash:
    PYTHONPATH=src python src/cli.py

    # Windows PowerShell:
    $env:PYTHONPATH="src"; python src/cli.py

    # Via Makefile:
    make cli

    # Via scripts:
    .\\scripts\\run.ps1 -Command cli
"""
import sys
from pathlib import Path

# Garante que src/ está no path quando executado diretamente
_SRC_DIR = Path(__file__).parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agente.config import get_settings
from agente.agent import run_agent
from logger.config import setup_logging


def main() -> None:
    """Loop interativo de chat via terminal."""
    settings = get_settings()
    setup_logging(level=settings.log_level, fmt="text")

    print("\n" + "=" * 60)
    print("  AGENTE DE ANÁLISE MACROECONÔMICA — CLI")
    print("  Versão 0.1.0 | Ambiente:", settings.app_env)
    print("=" * 60)
    print("\nIndicadores disponíveis:")
    print("  IPCA  |  Selic  |  Desocupação  |  Dólar  |  FBCF  |  Gini")
    print('\nDigite "sair" ou pressione Ctrl+C para encerrar.\n')

    while True:
        try:
            question = input("► Sua pergunta: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nEncerrando. Até logo!")
            break

        if question.lower() in ("sair", "exit", "quit", "q"):
            print("Até logo!")
            break

        if not question:
            continue

        print("\n⏳ Processando...\n")

        final_state = run_agent(question=question)

        print("─" * 60)
        print("📊 RESPOSTA DO AGENTE:")
        print("─" * 60)
        print(final_state.get("response") or "Não foi possível gerar uma resposta.")

        if final_state.get("plot_path"):
            print(f"\n📈 Gráfico salvo em: {final_state['plot_path']}")

        if final_state.get("error"):
            print(f"\n⚠️  Aviso: {final_state['error']}")

        print()


if __name__ == "__main__":
    main()
