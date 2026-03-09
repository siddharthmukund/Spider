FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
COPY webapp/requirements.txt ./webapp-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r webapp-requirements.txt

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
