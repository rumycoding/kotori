# Kotori Bot UI - Installation Guide

## Quick Fix for npm Dependency Issues

If you encounter the TypeScript version conflict error when running `npm install`, use one of these solutions:

### Option 1: Use Legacy Peer Deps (Recommended)
```bash
cd frontend
npm install --legacy-peer-deps
```

### Option 2: Force Installation
```bash
cd frontend
npm install --force
```

### Option 3: Clear Cache and Reinstall
```bash
cd frontend
npm cache clean --force
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

## Step-by-Step Installation

### 1. Prerequisites
- **Python 3.8+** - Download from https://python.org
- **Node.js 16+** - Download from https://nodejs.org
- **Anki** - Download from https://apps.ankiweb.net/
- **AnkiConnect Addon** - Install code `2055492159` in Anki

### 2. Environment Setup
```bash
# Clone or navigate to the project directory
# Copy the environment template
cp .env.example .env

# Edit .env with your Azure OpenAI credentials
# (Use your favorite text editor)
```

### 3. Backend Installation
```bash
cd backend
pip install -r requirements.txt
```

### 4. Frontend Installation
```bash
cd frontend
npm install --legacy-peer-deps
```

### 5. Start the Application

#### Option A: Use the Batch Script (Windows)
```bash
# From the root directory
start_kotori_ui.bat
```

#### Option B: Manual Start
```bash
# Terminal 1 - Backend
cd backend
python run_backend.py

# Terminal 2 - Frontend  
cd frontend
npm start
```

## Troubleshooting

### Common Issues

1. **"'react-scripts' is not recognized as an internal or external command"**
   - Delete `node_modules` and `package-lock.json` in frontend directory
   - Run `npm install --legacy-peer-deps`
   - If still failing, try: `npm install react-scripts --save --legacy-peer-deps`
   - Alternative: Use `npm run dev` instead of `npm start`

2. **"Cannot find module 'react'"**
   - Run `npm install --legacy-peer-deps` in the frontend directory
   - Ensure you're in the frontend directory when running npm commands

3. **Python module not found**
   - Make sure you're in the backend directory
   - Try `pip install -r requirements.txt` again

4. **Anki connection failed**
   - Ensure Anki is running
   - Install AnkiConnect addon (code: 2055492159)
   - Restart Anki after installing the addon

5. **Port already in use**
   - Change BACKEND_PORT in .env file
   - Or stop other services using ports 8000/3000

6. **Dependencies installation fails**
   - Clear npm cache: `npm cache clean --force`
   - Delete node_modules: `rm -rf node_modules package-lock.json`
   - Reinstall: `npm install --legacy-peer-deps`

### Development Mode

For development with hot reload:

```bash
# Backend (auto-reload on code changes)
cd backend
DEBUG_MODE=true python run_backend.py

# Frontend (auto-reload on code changes)
cd frontend
npm start
```

### Production Build

```bash
# Frontend production build
cd frontend
npm run build

# Backend production (install gunicorn first)
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Verification

Once everything is running:

1. Backend health check: http://localhost:8000/api/health
2. API documentation: http://localhost:8000/docs
3. Frontend application: http://localhost:3000

## Support

If you continue to have issues:

1. Delete `node_modules` and `package-lock.json` in frontend folder
2. Run `npm install --legacy-peer-deps`
3. Check that all required environment variables are set in `.env`
4. Ensure Anki is running with AnkiConnect addon installed

## Alternative Package Manager

If npm continues to cause issues, try using yarn:

```bash
# Install yarn globally
npm install -g yarn

# Install dependencies with yarn
cd frontend
yarn install

# Start with yarn
yarn start