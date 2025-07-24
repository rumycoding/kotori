
# Kotori 🐦 - Language Learning Bot

Kotori is an AI-powered language learning assistant that helps you practice English and Japanese through conversational learning. It integrates with Anki flashcards to provide personalized vocabulary practice and tracks your learning progress.

## 🌟 Features

-**Smart Conversation Flow**: State-based conversation management with two modes:

  -**Study Mode**: Structured learning with flashcard practice and assessment

  -**Chat Mode**: Free conversation with optional corrections

-**Anki Integration**: Seamlessly work with your existing Anki decks

-**Progress Tracking**: Automated assessment of vocabulary mastery

-**Multi-Language Support**: Currently supports English and Japanese learning

-**Multiple Interfaces**: CLI and Web UI options

-**Real-time Learning**: Dynamic difficulty adjustment based on your performance

## 🏗️ Architecture

### Core Components

-**`kotori_bot.py`**: The heart of Kotori - implements a LangGraph-based state machine for conversation flow

-**Anki Integration**: Tools for reading flashcards and tracking learning progress

-**Web Backend**: FastAPI-based REST API and WebSocket support

-**React Frontend**: Modern UI for interactive learning sessions

## 📋 Prerequisites

-**Python 3.8+**

-**Node.js 16+** (for Web UI)

-**Anki Desktop** (with AnkiConnect plugin for flashcard integration)

-**Azure OpenAI** account (for AI capabilities)

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash

git clonehttps://github.com/rumycoding/kotori.git

cd kotori


# Copy environment template

cp .env.example.env

```

### 2. Configure Environment Variables

Edit `.env` file with your credentials:

```env

# Azure OpenAI Configuration

AZURE_OPENAI_API_KEY=your_api_key_here

AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/

AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

AZURE_OPENAI_API_VERSION=2024-02-15-preview

AZURE_MODEL_NAME=gpt-4


# Application Insights (Optional)

APPLICATIONINSIGHTS_CONNECTION_STRING=your_connection_string

```

### 3. Install Dependencies

#### For CLI Only:

```bash

pip install-rrequirements.txt

```

#### For Full Setup (CLI + Web UI):

```bash

# Install Python dependencies

pip install-rrequirements.txt

pip install-rbackend/requirements.txt


# Install Node.js dependencies

cd frontend

npm install

cd ..

```

### 4. Setup Anki (Optional but Recommended)

1. Install [Anki Desktop](https://apps.ankiweb.net/)
2. Install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on
3. Create a deck named "Kotori" (or specify your deck name in configuration)
4. Ensure Anki is running when using Kotori

## 🖥️ Usage

### CLI Interface

Run Kotori in command line mode:

```bash

# Windows

scripts\run_chatbot_cli.bat


# Linux/Mac

python main.py

```

**CLI Features:**

- Direct conversation with Kotori
- All core learning features available
- Perfect for focused study sessions

### Web UI Interface

Start the full web application:

```bash

# Windows - Automated startup

scripts\start_kotori_ui.bat


# Manual startup

# Terminal 1: Start backend

cd backend

python run_backend.py


# Terminal 2: Start frontend

cd frontend

npm start

```

**Web UI Features:**

- Interactive chat interface
- Real-time conversation flow visualization
- Learning progress dashboard
- Session history and analytics
- Debug panels for development

Access the web interface at: `http://localhost:3000`

## 🧠 Understanding `kotori_bot.py`

The `kotori_bot.py` file is the core intelligence of Kotori, implementing a sophisticated state machine using LangGraph for managing conversation flow and learning sessions.

### Key Components

#### 1. **State Management (`KotoriState`)**

```python

class KotoriState(TypedDict):

    messages: Annotated[list, add_messages]  # Conversation history

    learning_goals: str                      # User's learning objectives

    active_cards: str                        # Current flashcard being practiced

    assessment_history: List[str]            # Learning progress tracking

    next: str                               # Next conversation state

    # ... additional state fields

```

#### 2. **Conversation Nodes**

The bot operates through discrete conversation states:

-**`greeting`**: Initial interaction and goal setting

-**`topic_selection_prompt`**: Mode selection (Study vs Chat)

-**`topic_selection`**: Internal routing logic

-**`retrieve_cards`**: Fetch relevant flashcards from Anki

-**`conversation`**: Structured vocabulary practice

-**`free_conversation`**: Open-ended chat mode

-**`assessment`**: Evaluate user's learning progress

-**`card_answer`**: Update flashcard difficulty based on performance

#### 3. **Smart Routing System**

The bot uses conditional edges and LLM-based decision making to:

- Adapt conversation flow based on user responses
- Switch between study and chat modes dynamically
- Determine when users have mastered vocabulary
- Route to appropriate learning activities

#### 4. **Tool Integration**

Seamless integration with Anki through specialized tools:

-`find_cards_to_talk_about`: Select practice vocabulary

-`add_anki_note`: Create new flashcards for struggled words

-`answer_card`: Update spaced repetition scheduling

-`check_anki_connection`: Ensure Anki connectivity

#### 5. **Assessment Engine**

Sophisticated evaluation system that analyzes:

-**Meaning Understanding**: Grasp of vocabulary concepts

-**Usage Accuracy**: Correct application in context

-**Naturalness**: Fluent, native-like usage

The assessment uses a 1-5 scale and provides specific feedback for targeted improvement.

#### 6. **Configuration System (`KotoriConfig`)**

Flexible configuration for different learning scenarios:

```python

config = {

    "language": "english",        # or "japanese"

    "deck_name": "MyDeck",       # Anki deck to practice

    "temperature": 0.1           # AI creativity level

}

```

### Conversation Flow Example

1.**Greeting** → User sets learning goals and level

2.**Mode Selection** → Choose Study Mode or Chat Mode

3.**Study Mode Path**:

- Retrieve flashcards from Anki
- Practice vocabulary in context
- Assess understanding
- Update flashcard scheduling
- Repeat or move to new vocabulary

4.**Chat Mode Path**:

- Free conversation with optional corrections
- Add new vocabulary to Anki when needed

## 📁 Project Structure

```

kotori/

├── kotoribot/

│   ├── kotori_bot.py          # 🧠 Core conversation engine

│   └── prompt.yaml            # Conversation prompts

├── anki/

│   ├── anki.py               # Anki integration tools

│   └── test_anki.py          # Anki functionality tests

├── backend/

│   ├── app/

│   │   ├── main.py           # FastAPI application

│   │   ├── models.py         # Data models

│   │   └── api/routes.py     # REST API endpoints

│   └── run_backend.py        # Backend server startup

├── frontend/

│   ├── src/

│   │   ├── components/       # React UI components

│   │   └── services/         # API and WebSocket clients

│   └── public/

├── scripts/

│   ├── run_chatbot_cli.bat   # CLI startup script

│   └── start_kotori_ui.bat   # Full UI startup script

├── main.py                   # CLI entry point

└── requirements.txt          # Python dependencies

```

## ⚙️ Configuration

### Language Settings

```python

# English learning mode

config = {"language": "english", "deck_name": "English_Vocabulary"}


# Japanese learning mode  

config = {"language": "japanese", "deck_name": "Japanese_Core"}

```

### AI Behavior

-**Temperature**: Controls AI creativity (0.0-2.0)

  -`0.1`: Focused, consistent responses (recommended for study)

  -`0.7`: More creative, varied responses (good for chat mode)

### Anki Integration

-**Deck Selection**: Choose which Anki deck to practice from

-**Auto-Add**: New vocabulary automatically added to "Kotori" deck

-**Spaced Repetition**: Assessment scores update card scheduling

## 🧪 Testing

```bash

# Run Anki integration tests

python -mpytestanki/test_anki.py


# Run all tests

python -mpytest

```

## 🔧 Development

### Adding New Conversation Nodes

1. Define node function in `kotori_bot.py`
2. Add to `_setup_nodes()` method
3. Configure routing in `_setup_edges()`

### Extending Anki Tools

1. Implement new tool in `anki/anki.py`
2. Add to tools list in `KotoriBot.__init__()`
3. Update relevant conversation nodes

### Frontend Development

```bash

cd frontend

npm rundev     # Development server with hot reload

npm runbuild   # Production build

```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with detailed description

## 📝 License

[License information to be added]

## 🆘 Troubleshooting

### Common Issues

**"Anki connection failed"**

- Ensure Anki Desktop is running
- Verify AnkiConnect add-on is installed and enabled
- Check firewall settings

**"Azure OpenAI authentication error"**

- Verify your `.env` file has correct credentials
- Check API key permissions and quota
- Ensure endpoint URL is correct

**"Frontend build fails"**

- Delete `node_modules` and run `npm install` again
- Check Node.js version compatibility
- Verify all environment variables are set

### Getting Help

- 📚 Check the `docs/` folder for detailed documentation
- 🐛 Report bugs via GitHub Issues
- 💬 Join our discussion board for questions

---

**Happy Learning with Kotori! 🐦✨**
