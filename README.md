# Kotori Chatbot

A simple yet powerful chatbot with memory capabilities built using LangChain and Azure OpenAI.

## Features

- Conversational AI powered by Azure OpenAI language models
- Persistent memory to remember past conversations
- Session-based chat history
- Simple command-line interface

## Requirements

- Python 3.8+
- Azure OpenAI service with an API deployment
- Azure OpenAI API key and endpoint

## Setup

1. **Install dependencies**
   
   Run the included installation script:

   ```
   install_dependencies.bat
   ```

   Or manually install with pip:

   ```
   pip install -r requirements.txt
   ```

2. **Configure your Azure OpenAI settings**
   
   Edit the `.env` file and replace the placeholder values with your actual Azure OpenAI settings:

   ```
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
   AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name_here
   AZURE_OPENAI_API_VERSION=2023-12-01-preview
   ```

## Running the chatbot

1. Use the included script:

   ```
   run_chatbot.bat
   ```

   Or run directly with Python:

   ```
   python main.py
   ```

2. Chat with Kotori in the command line interface
3. Type `exit`, `quit`, or `bye` to end the conversation

## How it works

Kotori uses LangChain to integrate with Azure OpenAI's language models and implements memory capabilities through:

1. Session-based chat history management
2. Persistent storage of conversations in JSON files
3. Loading previous conversations when resuming chats
4. Secure connection to Azure OpenAI services

## Customization

- Change the Azure OpenAI deployment by modifying the `AZURE_OPENAI_DEPLOYMENT_NAME` in your `.env` file
- Adjust the system prompt to change Kotori's personality
- Modify temperature and other parameters in the `AzureChatOpenAI` initialization
- Extend functionality by adding new features to the `ChatbotWithMemory` class

## Directory structure

```
kotori/
├── .env                    # Environment variables (API keys)
├── requirements.txt        # Python dependencies
├── main.py                 # Main chatbot code
├── install_dependencies.bat # Script to install dependencies
├── run_chatbot.bat         # Script to run the chatbot
└── memory/                 # Directory where chat histories are stored (created at runtime)
```

## License

MIT
