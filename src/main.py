# -*- coding: utf-8 -*-
"""
Ponto de entrada principal para interagir com o Agente de Pesquisa Econômica.

Este script inicia um loop de chat que permite ao usuário fazer perguntas
continuamente ao agente e receber as respostas.
"""

# =============================================================================
# ARQUIVO LEGADO — src/main.py (CLI)
# Este arquivo foi substituído por:
#   - src/cli.py     (interface de linha de comando)
#   - src/main_asgi.py  não existe: o entry point ASGI é src/main.py na NOVA estrutura
#
# Para rodar o servidor, use a partir da raiz do projeto:
#   PYTHONPATH=src uvicorn main:app --reload
#   (o main referenciado é src/main.py da NOVA estrutura — ver cli.py)
# =============================================================================

# Mantido para não quebrar referências existentes.
# Use src/cli.py para a interface CLI atualizada.

from agente.agent import run_agent


def main():
    """Loop interativo CLI (legado)."""
    print("=== Agente de Pesquisa Macroeconômica ===")
    print("Olá! Sou seu assistente para análise de dados macroeconômicos.")
    print('Digite "sair" para encerrar.\n')

    while True:
        question = input("Sua pergunta: ").strip()
        if question.lower() in ("sair", "exit", "quit"):
            print("Até logo!")
            break
        if not question:
            continue

        print("\nProcessando...\n")
        final_state = run_agent(question=question)

        print("--- RESPOSTA ---")
        print(final_state.get("response", "Não foi possível gerar uma resposta."))
        if final_state.get("plot_path"):
            print(f"\n[Gráfico salvo em: {final_state['plot_path']}]")
        print()


if __name__ == "__main__":
    main()
```

### Suas Próximas Ações:

1.  **Crie o novo arquivo:** Na pasta `src`, crie o arquivo `main.py`.
2.  **Execute o novo script:** Agora, em vez de rodar o `agent.py`, você vai rodar o `main.py`.
    ```bash
    python src/main.py
    
