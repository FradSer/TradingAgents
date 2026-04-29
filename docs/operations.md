# TradingAgents Operations Guide

## Quick Start

### Docker Hub Image (default)

```bash
# Pull image
docker pull fradser/tradingagents:v0.2.4-frad

# Run with env vars
docker run -d --name tradingagents \
  -e LLM_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-xxx \
  -v tradingagents_data:/home/appuser/.tradingagents \
  fradser/tradingagents:v0.2.4-frad sleep infinity

# Run analysis
docker exec tradingagents tradingagents analyze -t NVDA
```

### Docker Compose

```bash
cp .env.example .env
# Edit .env: set LLM_PROVIDER and API key

docker compose up -d tradingagents
docker exec tradingagents tradingagents analyze -t NVDA
```

### Build from Source

```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# Configure
cp .env.example .env
# Edit .env

# Build and run
docker compose up -d tradingagents
docker exec tradingagents tradingagents analyze -t NVDA
```

---

## CLI

### Command Forms

```
tradingagents analyze -t NVDA    # subcommand
tradingagents -t NVDA            # direct (equivalent)
tradingagents                    # interactive mode (no --ticker)
```

### Options

| Option | Short | Default | Env Var |
|---|---|---|---|
| `--ticker` | `-t` | — | — |
| `--date` | `-d` | today | — |
| `--provider` | `-p` | `openai` | `LLM_PROVIDER` |
| `--deep-model` | | `gpt-5.4` | `DEEP_THINK_MODEL` |
| `--quick-model` | | `gpt-5.4-mini` | `QUICK_THINK_MODEL` |
| `--backend-url` | | — | `OPENAI_COMPATIBLE_BASE_URL` |
| `--analysts` | | all | — |
| `--depth` | | `1` | — |
| `--language` | `-l` | `English` | — |
| `--checkpoint` | | `false` | — |
| `--clear-checkpoints` | | `false` | — |

Resolution: CLI flag > env var > built-in default.

### Examples

```bash
tradingagents analyze -t NVDA
tradingagents analyze -t NVDA -d 2024-05-10 --depth 3
tradingagents analyze -t NVDA -p openai-compatible \
  --backend-url http://host:8080/v1 \
  --deep-model mimo-v2.5-pro --quick-model mimo-v2.5
tradingagents analyze -t NVDA --analysts market,news --language Chinese
```

---

## LLM Providers

| Provider | Key | API Key Env Var |
|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Google | `google` | `GOOGLE_API_KEY` |
| xAI | `xai` | `XAI_API_KEY` |
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` |
| Qwen | `qwen` | `DASHSCOPE_API_KEY` |
| GLM | `glm` | `ZHIPU_API_KEY` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` |
| Azure | `azure` | `AZURE_OPENAI_API_KEY` + 3 more |
| Ollama | `ollama` | none |
| OpenAI-Compatible | `openai-compatible` | `OPENAI_API_KEY` (optional) |

### OpenAI-Compatible

For third-party APIs (vLLM, LiteLLM, xiaomimimo.com, etc.):

```bash
tradingagents analyze -t NVDA -p openai-compatible \
  --backend-url https://your-api.com/v1 \
  --deep-model your-model --quick-model your-model
```

Uses Chat Completions API (not Responses API). `--backend-url` is required.

### Azure OpenAI

```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
OPENAI_API_VERSION=2024-12-01-preview
```

---

## unRaid Deployment

### Template

File: `unraid/fradser-tradingagents.xml`

- Image: `fradser/tradingagents:v0.2.4-frad`
- Category: `Tools: Finance:`
- Entry: `sleep infinity` (persistent service, exec into it)

### Main Settings

| Setting | Env Var | Default |
|---|---|---|
| App Data | (path mount) | `/mnt/user/appdata/tradingagents` |
| Default LLM Provider | `LLM_PROVIDER` | `openai` |
| OpenAI API Key | `OPENAI_API_KEY` | — |
| Anthropic API Key | `ANTHROPIC_API_KEY` | — |
| Google API Key | `GOOGLE_API_KEY` | — |

### Advanced Settings

| Setting | Env Var |
|---|---|
| XAI API Key | `XAI_API_KEY` |
| DeepSeek API Key | `DEEPSEEK_API_KEY` |
| DashScope API Key | `DASHSCOPE_API_KEY` |
| ZhiPu API Key | `ZHIPU_API_KEY` |
| OpenRouter API Key | `OPENROUTER_API_KEY` |
| Alpha Vantage API Key | `ALPHA_VANTAGE_API_KEY` |
| OpenAI-Compatible Base URL | `OPENAI_COMPATIBLE_BASE_URL` |
| Quick Think Model | `QUICK_THINK_MODEL` |
| Deep Think Model | `DEEP_THINK_MODEL` |

### Usage

```bash
# unRaid Console
tradingagents analyze -t NVDA

# SSH (synchronous)
ssh -t root@NAS_IP "docker exec TradingAgents tradingagents analyze -t NVDA"

# SSH (detached)
ssh root@NAS_IP "docker exec -d TradingAgents sh -c \
  'tradingagents analyze -t NVDA > /home/appuser/.tradingagents/logs/NVDA.log 2>&1'"

# Check progress
ssh root@NAS_IP "docker exec TradingAgents tail -f /home/appuser/.tradingagents/logs/NVDA.log"

# Read result
ssh root@NAS_IP "docker exec TradingAgents cat \
  /home/appuser/.tradingagents/logs/NVDA/$(date +%Y-%m-%d)/reports/final_trade_decision.md"
```

### Deploy Template

```bash
scp unraid/fradser-tradingagents.xml \
  root@NAS_IP:/boot/config/plugins/dockerMan/templates-user/
```

### Gotcha

If using `OPENAI_COMPATIBLE_BASE_URL`, set `LLM_PROVIDER=openai-compatible`, NOT `openai`. The `openai` provider uses Responses API which most compatible endpoints don't support.

---

## Docker Build & Push

### Build

```bash
# Local (arch matches host)
docker build -t fradser/tradingagents:v0.2.4-frad .

# Cross-compile for x86_64
docker buildx build --platform linux/amd64 -t fradser/tradingagents:v0.2.4-frad .
```

### Push

```bash
docker push fradser/tradingagents:v0.2.4-frad
docker push fradser/tradingagents:latest
```

### Push Fails on Large Layer

Squash layers to reduce upload size:

```bash
docker export $(docker create fradser/tradingagents:v0.2.4-frad) | \
  docker import - fradser/tradingagents:squashed

cat > Dockerfile.entrypoint << 'EOF'
FROM fradser/tradingagents:squashed
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["tradingagents"]
EOF

docker build -f Dockerfile.entrypoint -t fradser/tradingagents:v0.2.4-frad .
docker push fradser/tradingagents:v0.2.4-frad
```

---

## Data & Logs

### Directory Structure

```
/home/appuser/.tradingagents/
  cache/                     # Market data cache (CSV)
  logs/
    NVDA/
      2026-04-29/
        reports/
          market_report.md
          sentiment_report.md
          news_report.md
          fundamentals_report.md
          investment_plan.md
          trader_investment_plan.md
          final_trade_decision.md
        message_tool.log     # Full agent conversation
  memory/
    trading_memory.md
```

### Read Results

```bash
docker exec TradingAgents cat \
  /home/appuser/.tradingagents/logs/NVDA/$(date +%Y-%m-%d)/reports/final_trade_decision.md
```

### Reports Per Analysis

| Report | Agent |
|---|---|
| `market_report.md` | Market Analyst |
| `sentiment_report.md` | Social Analyst |
| `news_report.md` | News Analyst |
| `fundamentals_report.md` | Fundamentals Analyst |
| `investment_plan.md` | Research Manager |
| `trader_investment_plan.md` | Trader |
| `final_trade_decision.md` | Portfolio Manager |

---

## Troubleshooting

### OpenAIError: api_key must be set

```bash
docker exec TradingAgents env | grep API_KEY
```

- `openai` provider: `OPENAI_API_KEY` required
- `openai-compatible` provider: `OPENAI_API_KEY` optional, `OPENAI_COMPATIBLE_BASE_URL` required

### exec format error

Architecture mismatch. Image built on ARM but running on x86 (or vice versa). Rebuild on target arch.

### Permission denied on data directory

```bash
mkdir -p /mnt/user/appdata/tradingagents
chown -R 1000:1000 /mnt/user/appdata/tradingagents
```

### docker exec -d output not visible

`docker exec -d` output does NOT go to `docker logs`. Always redirect:

```bash
docker exec -d TradingAgents sh -c \
  'tradingagents analyze -t NVDA > /home/appuser/.tradingagents/logs/NVDA.log 2>&1'
```
