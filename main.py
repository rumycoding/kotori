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

# # Configure OpenTelemetry
# # Create telemetry exporter
# exporter = AzureMonitorTraceExporter.from_connection_string(
#     os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
# )
# # Use the SDK TracerProvider and set it up just once
# tracer_provider = TracerProvider()
# span_processor = BatchSpanProcessor(exporter, schedule_delay_millis=60000)
# tracer_provider.add_span_processor(span_processor)
# # Set the configured tracer provider just once
# trace.set_tracer_provider(tracer_provider)
# tracer = trace.get_tracer(__name__)
# LangChainInstrumentor().instrument()

# Print environment variables for debugging
print("Debug: Environment variables:")
print(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
print(f"AZURE_OPENAI_DEPLOYMENT_NAME: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
print(f"AZURE_OPENAI_API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
print("AZURE_OPENAI_API_KEY: [REDACTED]")  # Don't print the actual key for security
print(f"APPLICATIONINSIGHTS_CONNECTION_STRING: {os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING', '[NOT SET]')}")
print(f"AZURE_MODEL_NAME: {os.getenv('AZURE_MODEL_NAME')}")


model = AzureChatOpenAI(
    model=os.environ["AZURE_MODEL_NAME"],   # add this to make sure token_counter in trim_messages is working properly
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    api_key=SecretStr(os.environ["AZURE_OPENAI_API_KEY"])
)

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
from langchain_core.messages import SystemMessage, trim_messages

# insert system message and language
prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant. Answer all questions to the best of your ability in {language}. The provided chat history may include a summary of the earlier conversation.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str

# Define a new graph, this allows the history message be stored in its state
workflow = StateGraph(state_schema=State)

# this trims the message, makes sure it does not exceed certain number of tokens
trimmer = trim_messages(
    max_tokens=6000,
    strategy="last",
    token_counter=model,
    include_system=True,
    allow_partial=False,
    start_on="human",
)

# Define the function that calls the model
def call_model(state: State):
    ## trim the message
    # trimmed_messages = trimmer.invoke(state["messages"])
    # print(trimmed_messages)
    # prompt = prompt_template.invoke(
    #     {"messages": trimmed_messages, "language": state["language"]}
    # )
    # response = model.invoke(prompt)
    # return {"messages": [response]}

    ## summarize the message
    message_history = state["messages"][:-1]  # exclude the most recent user input
    if len(message_history) >= 4:
        last_human_message = state["messages"][-1]
        # Invoke the model to generate conversation summary
        summary_prompt = (
            "Distill the above chat messages into a single summary message. Be aware of human message and AI message."
            "Include as many specific details as you can. Your response should start with 'Chat History summary:'"
        )
        summary_message = model.invoke(
            message_history + [HumanMessage(content=summary_prompt)]
        )

        # Delete messages that we no longer want to show up
        # This remove all messages in the state
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"]]
        # Re-add user message
        human_message = HumanMessage(content=last_human_message.content)
        trimmed_messages = [summary_message, human_message]

        # Call the model with summary & response
        prompt = prompt_template.invoke(
            {"messages": trimmed_messages, "language": state["language"]}
        )
        response = model.invoke(prompt)
        print(response)
        message_updates = [summary_message, human_message, response] + delete_messages
    else:
        prompt = prompt_template.invoke(
            {"messages": state["messages"], "language": state["language"]}
        )
        message_updates = [model.invoke(prompt)]
    return {"messages": message_updates}


# Define the (single) node in the graph
workflow.add_edge(START, "model")
workflow.add_node("model", call_model)

# Add memory, so that the workflow remember the chat history
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

demo_ephemeral_chat_history = [
    HumanMessage(content="Hey there! I'm Nemo."),
    AIMessage(content="Hello!"),
    HumanMessage(content="How are you today?"),
    AIMessage(content="Fine thanks!"),
]

response= app.invoke(
    {
        "messages": demo_ephemeral_chat_history
        + [HumanMessage(content="What's my name?")],
        "language": "Japanese"
    },
    config={"configurable": {"thread_id": "2"}},
)

# Print all messages from the response
messages = response["messages"]
for i, message in enumerate(messages):
    message.pretty_print()


# config = {"configurable": {"thread_id": "2"}}
# query = "Who am I?"
# language = "Japanese"

# # Will stream the response of the AI output 
# input_messages = [HumanMessage(query)]
# for chunk, metadata in app.stream(
#     {"messages": input_messages, "language": language},
#     config,
#     stream_mode="messages",
# ):
#     if isinstance(chunk, AIMessage):  # Filter to just model responses
#         print(chunk.content, end="|")
