FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 安装 nanobot 正式版
RUN pip install --no-cache-dir nanobot-ai

# 初始化 nanobot 目录结构（非交互）
RUN mkdir -p /root/.nanobot/workspace && \
    test -f /root/.nanobot/config.json || echo '{}' > /root/.nanobot/config.json

# ── 工作区文件 ──
WORKDIR /root/.nanobot/workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有工作区代码
COPY AGENTS.md SOUL.md USER.md TOOLS.md HEARTBEAT.md ./
COPY *.py ./
COPY *.json ./

# ── nanobot 全局配置 ──
COPY docker-config.json /root/.nanobot/config.json

# 暴露 gateway 端口
EXPOSE 18790

# 以 gateway 模式启动
CMD ["nanobot", "gateway"]
