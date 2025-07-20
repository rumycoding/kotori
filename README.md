# Kotori Bot - Comprehensive Language Learning UI

A modern, feature-rich user interface for the Kotori Language Learning Bot system, built with React frontend and FastAPI backend.

## 🌟 Features

### Core Functionality
- **Real-time Chat Interface** - Interactive conversation with AI language tutor
- **Voice Input & Output** - Speech recognition and text-to-speech capabilities
- **Multi-language Support** - Currently supports English and Japanese learning
- **Anki Integration** - Seamless flashcard management and learning

### Advanced Features
- **Real-time Assessment** - Live conversation analysis and progress tracking
- **Debug Panel** - State graph visualization and tool call monitoring
- **Conversation History** - Search, export, and manage chat history
- **Responsive Design** - Mobile-friendly interface with dark/light themes
- **WebSocket Communication** - Real-time bidirectional communication

### Technical Features
- **State Graph Visualization** - Interactive display of conversation flow
- **Tool Call Monitoring** - Real-time tracking of function executions
- **Error Handling** - User-friendly error notifications and recovery
- **Performance Optimized** - Efficient state management and updates

## 🏗️ Architecture

```
kotori-ui/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # REST API routes
│   │   ├── websocket/   # WebSocket handlers
│   │   ├── models/      # Pydantic models
│   │   ├── services/    # Business logic
│   │   └── main.py      # FastAPI application
│   ├── kotoribot/       # Original bot code
│   └── anki/           # Anki integration
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── services/    # API/WebSocket services
│   │   ├── types/       # TypeScript definitions
│   │   └── App.tsx      # Main application
│   └── public/          # Static files
└── docs/               # Documentation
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** with pip
2. **Node.js 16+** with npm
3. **Anki** with AnkiConnect addon installed
4. **Azure OpenAI** account and API keys

### Environment Setup

1. Clone the repository and navigate to the project directory

2. Copy `.env.example` to `.env` and configure:
```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_MODEL_NAME=gpt-4

# Optional: Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=your_connection_string

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DEBUG_MODE=true

# Frontend Configuration
FRONTEND_URL=http://localhost:3000
```

### Backend Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Start the backend:**
```bash
python run_backend.py
```

The backend will be available at `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start the development server:**
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

### Anki Setup

1. **Install Anki** from https://apps.ankiweb.net/
2. **Install AnkiConnect addon:**
   - Tools → Add-ons → Get Add-ons
   - Code: `2055492159`
3. **Restart Anki**
4. **Create or ensure "Kotori" deck exists**

## 🔧 Configuration

### Backend Configuration

The backend can be configured through environment variables or the `.env` file:

- `AZURE_OPENAI_*`: Azure OpenAI service configuration
- `BACKEND_HOST/PORT`: Server binding configuration
- `DEBUG_MODE`: Enable development features
- `FRONTEND_URL`: CORS configuration for frontend

### Frontend Configuration

Frontend settings are managed through the UI and stored in localStorage:

- **Theme**: Light/Dark mode selection
- **Voice Settings**: TTS rate, pitch, volume, auto-play
- **Debug Options**: Show/hide debug panels
- **Language**: Learning language selection

## 🛠️ Development

### Backend Development

1. **Install development dependencies:**
```bash
pip install -r requirements.txt
pytest  # for testing
```

2. **Run in development mode:**
```bash
DEBUG_MODE=true python run_backend.py
```

3. **API Testing:**
   - Use the Swagger UI at `http://localhost:8000/docs`
   - WebSocket testing with tools like Postman or custom clients

### Frontend Development

1. **Install development dependencies:**
```bash
npm install
```

2. **Available scripts:**
```bash
npm start          # Development server with hot reload
npm run build      # Production build
npm test           # Run tests
npm run lint       # Code linting
npm run lint:fix   # Auto-fix linting issues
```

3. **Component Development:**
   - Components are in `src/components/`
   - Use TypeScript for type safety
   - Follow Material-UI design patterns

## 📡 API Documentation

### REST Endpoints

- `GET /api/health` - System health check
- `POST /api/sessions` - Create new chat session
- `GET /api/sessions/{id}` - Get session details
- `PUT /api/sessions/{id}/config` - Update session configuration
- `GET /api/sessions/{id}/history` - Get conversation history
- `POST /api/sessions/{id}/history/export` - Export conversation

### WebSocket Events

Connect to: `ws://localhost:8000/ws/chat/{session_id}`

**Client → Server:**
```json
{
  "event_type": "user_message",
  "data": {
    "message": "Hello, how are you?",
    "session_id": "uuid"
  }
}
```

**Server → Client:**
```json
{
  "event_type": "ai_response",
  "data": {
    "message": {
      "id": "uuid",
      "content": "I'm doing well, thank you!",
      "message_type": "ai",
      "timestamp": "2025-01-20T12:00:00Z"
    }
  },
  "session_id": "uuid"
}
```

## 🔍 Troubleshooting

### Common Issues

1. **Backend won't start:**
   - Check environment variables in `.env`
   - Ensure Python dependencies are installed
   - Verify Anki is running with AnkiConnect

2. **Frontend can't connect:**
   - Check backend is running on port 8000
   - Verify CORS configuration
   - Check browser console for errors

3. **Anki integration not working:**
   - Ensure Anki is running
   - Verify AnkiConnect addon is installed and enabled
   - Check firewall settings

4. **Voice features not working:**
   - Check browser permissions for microphone
   - Ensure HTTPS in production for voice features
   - Verify speech synthesis API support

### Debug Mode

Enable debug mode for additional logging:

**Backend:**
```bash
DEBUG_MODE=true python run_backend.py
```

**Frontend:**
- Use the debug panel toggle in the UI
- Check browser developer tools console
- Enable debug mode in settings panel

## 🧪 Testing

### Backend Testing
```bash
cd backend
pytest
pytest --cov=app  # with coverage
```

### Frontend Testing
```bash
cd frontend
npm test
npm test -- --coverage  # with coverage
```

### Manual Testing

1. **Health Check:**
```bash
curl http://localhost:8000/api/health
```

2. **WebSocket Test:**
Use browser console or WebSocket testing tools to connect to `ws://localhost:8000/ws/chat/test-session`

## 📈 Performance Considerations

- **WebSocket connections** are managed per session
- **Message history** is stored in memory (consider database for production)
- **Voice processing** happens client-side
- **Assessment calculations** are done server-side
- **State updates** are batched for efficiency

## 🔒 Security

- CORS is configured for development (update for production)
- WebSocket connections should be authenticated in production
- API rate limiting should be implemented for production
- Environment variables should be secured in production

## 🚀 Deployment

### Production Backend
```bash
# Use production ASGI server
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Production Frontend
```bash
npm run build
# Serve build/ directory with nginx or similar
```

## 📄 License

This project is part of the Kotori Language Learning Bot system.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check existing issues in the repository
4. Create a new issue with detailed information

---

Built with ❤️ for language learners everywhere.
