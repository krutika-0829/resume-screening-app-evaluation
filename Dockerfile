FROM python:3.11-slim

WORKDIR /app

# install supervisor to run both services
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy all project files
COPY . .

# copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# expose both ports
EXPOSE 7860 8000

# start both services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]