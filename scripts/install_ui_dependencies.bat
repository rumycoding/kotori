@echo off
echo Installing backend dependencies for Kotori chatbot...
pip install -r backend/requirements.txt
echo Done! Dependencies installed successfully.
echo.
echo Remember to update your OpenAI API key in the .env file before running the chatbot UI.
echo.
pause
