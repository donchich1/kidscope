FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/data  # Створення папки data
COPY adminkidscopetg.py ./
CMD ["streamlit", "run", "adminkidscopetg.py"]