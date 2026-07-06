FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=0

WORKDIR /app


RUN apt-get update && apt-get install -y \
    curl wget ca-certificates \
    libnss3 libatk1.0-0 libgtk-3-0 \
    libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*


RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml .

RUN uv pip install --system .


RUN python -m playwright install chromium

COPY . .

CMD ["python", "src/main.py"]