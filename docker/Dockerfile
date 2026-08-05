FROM python:3.11-slim

# Install system deps (pandoc for pypandoc; add gettext for some platforms)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      pandoc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency file first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip
RUN pip install -r /app/requirements.txt
# Install Streamlit for the UI
RUN pip install streamlit

# Copy the rest of the repository
COPY . /app

EXPOSE 8501

CMD ["streamlit", "run", "tools/setup_ui.py", "--server.port", "8501", "--server.headless", "true"]
