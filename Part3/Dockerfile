FROM python:3.12-slim

WORKDIR /app

## Dependencies are copied and installed before the application code, so that
## editing chatbot.py does not invalidate the cached pip install layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY chatbot.py .

## Streamlit listens here. The same port must be given to ECS Express Mode.
EXPOSE 8501

CMD ["streamlit", "run", "chatbot.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
