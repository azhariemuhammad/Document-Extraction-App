FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY core core
COPY profiles profiles
ENV PYTHONUNBUFFERED=1 CACHE_DIR=/data/cache
EXPOSE 8501
CMD ["streamlit", "run", "app/ui.py", "--server.address=0.0.0.0", "--server.port=8501", "--browser.gatherUsageStats=false"]
