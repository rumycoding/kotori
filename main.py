"""
Kotori - A chatbot with memory using LangChain and Azure OpenAI
"""

import os
import sys
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

from anki.anki import (
    add_anki_note,
    check_anki_connection,
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

prompt = (
    "You are a helpful assistant to help user learn language. "
    "You have access to the anki. Please use deck 'Kotori'. If you find that the user does not know a word while chatting, you could add a note in anki. If the user does not have topic to talk about, you could find_cards_to_talk_about and evaluate how the user know the word and answer the card. If you encounter any error, ask the user to take action. You may not need to use tools for every query - the user may just want to chat!"
)

tools = [add_anki_note,
    check_anki_connection,
    get_note_by_id,
    search_notes_by_content,
    find_cards_to_talk_about,
    answer_card,
    answer_multiple_cards]

from langgraph.prebuilt import create_react_agent

from langchain.agents import AgentExecutor

# prompt allows you to preprocess the inputs to the model inside ReAct agent
# in this case, since we're passing a prompt string, we'll just always add a SystemMessage
# with this prompt string before any other messages sent to the model
agent = create_react_agent(model, tools, prompt=prompt)

# Create an agent executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Simple REPL demo
if __name__ == "__main__":
    print("Welcome to your ReAct Anki Agent! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Agent: Goodbye! 👋")
            break
        # Use invoke on the executor
        result = agent_executor.invoke({"input": user_input})
        print(f"Agent: {result['output']}\n")
