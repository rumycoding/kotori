"""
Kotori - A chatbot with memory using LangChain and Azure OpenAI
"""

import os
import sys
from typing import Dict, List
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import SecretStr
from langchain_core.messages import HumanMessage, AIMessage
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
    "APPLICATIONINSIGHTS_CONNECTION_STRING"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: The following required environment variables are missing: {', '.join(missing_vars)}")
    print("Please set these variables in the .env file.")
    sys.exit(1)

# Azure OpenAI deployment name - this corresponds to the model you've deployed in Azure OpenAI
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")  # Default to empty string if not set

# Configure OpenTelemetry
# Create telemetry exporter
exporter = AzureMonitorTraceExporter.from_connection_string(
    os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
)
# Use the SDK TracerProvider and set it up just once
tracer_provider = TracerProvider()
span_processor = BatchSpanProcessor(exporter, schedule_delay_millis=60000)
tracer_provider.add_span_processor(span_processor)
# Set the configured tracer provider just once
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)
LangChainInstrumentor().instrument()

# Print environment variables for debugging
print("Debug: Environment variables:")
print(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
print(f"AZURE_OPENAI_DEPLOYMENT_NAME: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
print(f"AZURE_OPENAI_API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
print("AZURE_OPENAI_API_KEY: [REDACTED]")  # Don't print the actual key for security
print(f"APPLICATIONINSIGHTS_CONNECTION_STRING: {os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING', '[NOT SET]')}")


model = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    api_key=SecretStr(os.environ["AZURE_OPENAI_API_KEY"])
)

# invoke a message
response =model.invoke(
    [
        HumanMessage(content="Hi! I'm Bob"),
        AIMessage(content="Hello Bob! How can I assist you today?"),
        HumanMessage(content="What's my name?"),
    ]
)
print(response.content)
