# Unraid deployment template

`fradser-tradingagents.xml` deploys TradingAgents 0.7.1 as a CLI-only container
(no WebUI, no published port). The image is built from the upstream `v0.7.1`
tag and published on Docker Hub as `fradser/tradingagents:v0.7.1-frad` and
`fradser/tradingagents:latest`.

Current deployment on frad-nas (10.10.0.195):

- Endpoint name: **magpie** — Magpie gateway `http://10.10.0.195:3425/v1`
- Quick and deep model: `hunyuan-eval/hy4-dev`
- `TRADINGAGENTS_LLM_PROVIDER=openai` with `TRADINGAGENTS_LLM_BACKEND_URL`
  pointing at the gateway (the generic `openai_compatible` entry suppresses
  `tool_choice` and produces `REVIEW` ratings)
- Data: `/mnt/user/appdata/tradingagents` -> `/home/appuser/.tradingagents`
- The container idles on `sleep infinity`; analyses run through `docker exec`.

Headless usage (v0.7.1 CLI):

```
docker exec TradingAgents tradingagents --ticker NVDA --date 2026-11-06 \
  --analysts market,news --save --no-show
```

The v0.2.4 flags `--provider`, `--deep-model`, `--quick-model`,
`--backend-url`, `--depth`, `-l` and the `analyze` subcommand no longer exist;
provider, models, language and debate/risk rounds come from `TRADINGAGENTS_*`
variables in the template. Section reports land in
`logs/<TICKER>/<DATE>/reports/`; `complete_report.md` / `complete_report.html`
land in `logs/reports/<TICKER>_<STAMP>/`.

`legacy/v0.2.4-frad` preserves the earlier customised fork code (non-interactive
CLI, `openai-compatible` provider, news-vendor patches). That code is no longer
the deployment source: the container image is built from upstream v0.7.1.

Tag `v0.7.1-frad` matches the Docker Hub image tag.
