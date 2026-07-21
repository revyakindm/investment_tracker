FROM apache/airflow:3.3.0-python3.11
COPY requirements.txt /
USER airflow
RUN pip install --no-cache-dir -r /requirements.txt