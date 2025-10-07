# -*- coding: utf-8 -*-
"""
Servidor web FastAPI para expor o Agente de Pesquisa Econômica como uma API.
"""

import base64
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importa a aplicação 'app' compilada do nosso módulo de agente
from agent import app as agent_app

# Define o modelo de dados para a requisição
class Query(BaseModel):
    question: str

# Inicializa a aplicação FastAPI
app = FastAPI(
    title="API do Agente de Pesquisa Econômica",
    description="Permite interagir com o agente de IA via requisições HTTP.",
    version="1.0.0"
)

# Configura o CORS para permitir que o HTML se comunique com o servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens (para desenvolvimento)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask-agent")
async def ask_agent(query: Query):
    """
    Endpoint principal para fazer uma pergunta ao agente.
    Recebe uma pergunta, invoca o agente LangGraph e retorna a resposta.
    """
    try:
        print(f"Recebida nova pergunta: {query.question}")
        
        # Define o estado inicial para a invocação do agente
        initial_state = {"question": query.question, "intermediate_steps": []}

        # Invoca o agente de forma síncrona (adequado para este caso)
        final_state = agent_app.invoke(initial_state)

        response_data = {
            "text": final_state.get('response', 'Não consegui gerar uma resposta.'),
            "plot_base64": None
        }

        # Se um gráfico foi gerado, lê o arquivo, codifica em Base64 e o inclui na resposta
        plot_path = final_state.get('plot_path')
        if plot_path:
            try:
                with open(plot_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    response_data["plot_base64"] = f"data:image/png;base64,{encoded_string}"
                print("Gráfico codificado em Base64 e incluído na resposta.")
            except Exception as e:
                print(f"Erro ao codificar o gráfico: {e}")

        return response_data

    except Exception as e:
        print(f"Erro durante a execução do agente: {e}")
        return {"text": f"Ocorreu um erro interno: {e}", "plot_base64": None}

@app.get("/")
def read_root():
    return {"status": "Agente de Pesquisa Econômica está online."}
