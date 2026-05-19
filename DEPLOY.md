# AI Investor Agent 部署指南

## 前提

- Linux VPS (Ubuntu 22.04+, 512MB RAM 够用)
- Python 3.11+
- Discord Bot Token + DeepSeek API Key

## 第一步：服务器初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 装 Python 3.11+（Ubuntu 22.04 自带 3.10，需升级）
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3.12 python3.12-venv python3-pip -y
```

## 第二步：安装 nanobot 正式版

```bash
pip install nanobot-ai

# 初始化（创建 ~/.nanobot/ 目录结构）
nanobot onboard
```

## 第三步：部署工作区文件

```bash
# 把 ai-investor-agent 的所有文件复制进去
cd ~/.nanobot/workspace
git clone https://github.com/你的用户名/ai-investor-agent.git tmp
cp -r tmp/* . && cp -r tmp/.git . 2>/dev/null
rm -rf tmp

# 或手动 rsync
rsync -av /path/to/ai-investor-agent/ ~/.nanobot/workspace/
```

## 第四步：安装 Python 依赖

```bash
cd ~/.nanobot/workspace
pip install -r requirements.txt
```

## 第五步：设置环境变量

```bash
# 添加到 ~/.bashrc 或创建 systemd service 时设置
export DEEPSEEK_API_KEY="sk-xxxxxxxx"
export AI_INVESTOR_DISCORD_TOKEN="MTE-xxxxxxxx"
```

## 第六步：合并 config.json

当前 workspace 里的 `config.json` 可直接用，但需要确认路径：

```json
"agents": {
  "defaults": {
    "workspace": "~/.nanobot/workspace",
    ...
  }
}
```

或者让 `nanobot onboard` 生成的 config 和我们的 config 合并（主要是添加上我们的 provider 和 channel 配置）。

## 第七步：启动

```bash
# 前台测试
nanobot gateway

# 正式运行（用 tmux 保持后台）
tmux new -s nanobot
nanobot gateway
# Ctrl+B, D 断开
```

## 环境变量对照

| 变量 | 用途 | 对应配置 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek LLM | `providers.deepseek.apiKey` |
| `AI_INVESTOR_DISCORD_TOKEN` | Discord Bot | `channels.discord.token` |

配置中使用 `${VAR}` 语法，nanobot 会自动从环境变量读取。
