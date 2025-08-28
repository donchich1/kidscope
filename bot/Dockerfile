FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY kidscopetg.py ./
COPY data/data.json /app/data/
CMD ["python", "kidscopetg.py"]
