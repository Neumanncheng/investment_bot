FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "nanobot-ai[discord]"

RUN mkdir -p /root/.nanobot/workspace

WORKDIR /root/.nanobot/workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY AGENTS.md SOUL.md USER.md TOOLS.md HEARTBEAT.md README.md ./
COPY pyproject.toml ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY config.json ./
COPY cron/ ./cron/

RUN pip install --no-cache-dir -e .

# 预创建挂载文件，防止 Docker Desktop 将缺失文件创建为目录
RUN touch /root/.nanobot/workspace/scan_schedule.json \
          /root/.nanobot/workspace/strategy_profile.json \
          /root/.nanobot/workspace/trades.jsonl \
          /root/.nanobot/workspace/src/portfolio_state.json \
          /root/.nanobot/workspace/src/latest_signals.json

# nanobot 全局配置（自动适配容器内路径）
RUN sed 's|"workspace": ".*"|"workspace": "/root/.nanobot/workspace"|' config.json > /root/.nanobot/config.json

EXPOSE 18790
CMD ["nanobot", "gateway"]
