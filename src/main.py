# -*- coding: utf-8 -*-
"""
Ponto de entrada principal para interagir com o Agente de Pesquisa Econômica.

Este script inicia um loop de chat que permite ao usuário fazer perguntas
continuamente ao agente e receber as respostas.
"""

# Importa a aplicação 'app' compilada do nosso módulo de agente
from agent import app, AgentState

def main():
    """
    Função principal que gerencia o loop de interação com o usuário.
    """
    print("--- Agente de Pesquisa Econômica ---")
    print('Olá! Sou seu assistente para análise de dados macroeconômicos.')
    print('Faça uma pergunta ou digite "sair" para terminar.')

    while True:
        # Pede uma pergunta ao usuário
        question = input("\nSua pergunta: ")

        # Condição de saída do loop
        if question.lower() == "sair":
            print("Até logo!")
            break

        # Define o estado inicial para a invocação do agente
        initial_state = {"question": question, "intermediate_steps": []}

        # Invoca o agente com a pergunta do usuário
        print("\nProcessando sua pergunta...")
        final_state = app.invoke(initial_state)

        # Exibe a resposta final de forma limpa
        print("\n--- RESPOSTA DO AGENTE ---")
        print(final_state.get('response', 'Não consegui gerar uma resposta.'))
        
        # Informa onde o gráfico foi salvo, se ele foi criado
        if final_state.get('plot_path'):
            print(f"-> Um gráfico de visualização foi salvo em: {final_state.get('plot_path')}")

if __name__ == '__main__':
    main()
```

### Suas Próximas Ações:

1.  **Crie o novo arquivo:** Na pasta `src`, crie o arquivo `main.py`.
2.  **Execute o novo script:** Agora, em vez de rodar o `agent.py`, você vai rodar o `main.py`.
    ```bash
    python src/main.py
    
