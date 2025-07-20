"""
Kotori - A chatbot with memory using LangChain and Azure OpenAI
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr
from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from kotoribot.kotori_bot import KotoriBot, KotoriConfig

from anki.anki import (
    add_anki_note,
    _check_anki_connection_internal,
    check_anki_connection,
    create_anki_deck,
    get_note_by_id,
    search_notes_by_content,
    find_cards_to_talk_about,
    answer_card,
    answer_multiple_cards
)


# Load environment variables from .env file
# Specify the path to the .env file explicitly
# Seems that if an env variable already exists, it will not be loaded again!
load_dotenv()

# Check for required Azure OpenAI environment variables
required_env_vars = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_API_VERSION",
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
    "AZURE_MODEL_NAME"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: The following required environment variables are missing: {', '.join(missing_vars)}")
    print("Please set these variables in the .env file.")
    sys.exit(1)

# Azure OpenAI deployment name - this corresponds to the model you've deployed in Azure OpenAI
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")  # Default to empty string if not set

model = AzureChatOpenAI(
    model=os.environ["AZURE_MODEL_NAME"],   # add this to make sure token_counter in trim_messages is working properly
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    api_key=SecretStr(os.environ["AZURE_OPENAI_API_KEY"])
)

# Check if deck Kotori exists, if not create it
try:
    ankiConnection = _check_anki_connection_internal().json()
    if ankiConnection.get("error"):
        raise Exception(ankiConnection["error"])
    
    create_result = create_anki_deck.invoke({
        "deck_name": "Kotori",
    })
    
except Exception as e:
    print(f"Anki connection error: {str(e)}")
    print("Anki connection failed. Please ensure Anki is running and the AnkiConnect plugin is installed.")
    sys.exit(1)

from langgraph.prebuilt import create_react_agent

# Create the ReAct agent using LangGraph
# This returns a compiled graph that can be invoked directly
from langgraph.checkpoint.memory import MemorySaver



# Simple REPL demo
async def main():
    print("Welcome to your ReAct Anki Agent! Type 'exit' to quit.")
    config: KotoriConfig = {
        "language": "english",
        "deck_name": "Kotori"
    }
    
    bot = KotoriBot(model, config)
    await bot.run_conversation()

if __name__ == "__main__":
    asyncio.run(main())
