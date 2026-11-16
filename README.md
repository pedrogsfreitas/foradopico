# ForaDoPico

Escala presencial inteligente para quem usa trem e metrô no horário de pico.
Global Solution FIAP 2026.2 · CitizenTech · Engenharia de Software 4ES.

## Integrantes

| Nome completo | RM |
|---|---|
| Pedro Guerra | RM______ |
| João Pedro ______ | RM______ |
| Matheus Haruo ______ | RM______ |

## Ficha Técnica do MVP

| Campo | Descrição |
|---|---|
| **Nome do produto** | ForaDoPico |
| **Cidadão e território** | Trabalhador CLT que usa trem e metrô no horário de pico na Grande São Paulo |
| **Problema, em uma frase** | Escalas presenciais montadas sem olhar o transporte jogam todo mundo no mesmo dia e horário, justamente no pico |
| **Proposta de valor** | Viaje fora do aperto: saiba quando sair para pegar o trem mais vazio, e ajude a cidade a respirar no horário de pico |
| **Arquitetura: componentes** | API (FastAPI) e front (React) na mesma imagem; pipeline de dados (Airflow e Databricks); robô RPA (Python); visão computacional (YOLO); assistente (LLM local com RAG); dispositivo ESP32 |
| **Fontes de dados** | Demanda por estação do portal de transparência do Metrô de SP; clima do Open-Meteo; views da camada Ouro `vw_app_lotacao_prevista` e `vw_app_minha_semana` |
| **Modelos de IA utilizados** | A CONFIRMAR com a equipe: YOLO para contagem de pessoas; LLM local com RAG para o assistente |
| **URL do MVP e repositório** | URL: A PREENCHER após o deploy · Repositório: este |
| **Indicadores de impacto** | Horas devolvidas ao funcionário por mês; viagens no pico evitadas por funcionário; lotação média evitada; dias com plano B acionado |
| **ODS conectados** | ODS 11 (cidades sustentáveis), ODS 3 (saúde e bem-estar), ODS 9 (inovação e infraestrutura), ODS 10 (redução das desigualdades) |

Repositórios das outras disciplinas: [Big Data](https://github.com/saborido613/foradopico-bigdata) · [RPA](https://github.com/haruoooo/SemestralRpa).

## O que já funciona

| Tela | Dados | Endpoint |
|---|---|---|
| Lotação prevista | `vw_app_lotacao_prevista` (Ouro · Databricks) | `GET /api/crowdingForecast` |
| Minha semana | `vw_app_minha_semana` (Ouro · Databricks) | `GET /api/myWeek` |

Também: `GET /health`, `GET /metrics` (Prometheus) e a documentação interativa em `/api/docs`.
Os endpoints do contrato com o robô RPA estão em [docs/productApiContract.yaml](docs/productApiContract.yaml) e entram na próxima etapa.

## Como rodar

Pré-requisito: Docker com Docker Compose.

```bash
cp .env.example .env      # troque a senha do Grafana
docker compose up --build
```

| Serviço | Endereço |
|---|---|
| App | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (dashboard "ForaDoPico · 4 métricas de ouro") |

### Sem Docker (desenvolvimento)

```bash
# API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# Front, em outro terminal
cd web
npm ci
npm run dev        # http://localhost:5173, com /api repassado para a porta 8000
```

### Testes

```bash
cd api && python -m pytest -q
```

## Estrutura

```
api/          API FastAPI, dados da Ouro e testes
web/          Front React (Vite)
monitoring/   Prometheus, regras de alerta e dashboard do Grafana
infra/        Terraform da nuvem
docs/         Contrato da API com o robô RPA
.github/      Pipeline do GitHub Actions
```

## Container

- Build em duas etapas: o Node só existe na etapa de build do front; a imagem final tem Python e os arquivos da aplicação.
- A aplicação roda com o usuário `10001`, sem privilégios e sem shell.
- Nenhum segredo entra na imagem: `.env` fica fora do contexto de build (`.dockerignore`).
- No compose, o app sobe com sistema de arquivos somente leitura, sem capabilities e com `no-new-privileges`.

## Pipeline DevSecOps

`.github/workflows/pipeline.yml` roda a cada push e pull request:

| Etapa | Ferramenta | Barra o pipeline quando |
|---|---|---|
| Build e testes | pytest e Vite | um teste falha ou o front não compila |
| Segredos | Gitleaks | encontra chave, token ou senha no histórico |
| Análise estática | Semgrep | encontra falha grave no código |
| Configuração | Trivy `config` | Dockerfile, compose ou Terraform com falha alta ou crítica |
| Imagem | Trivy `image` | a imagem tem vulnerabilidade alta ou crítica com correção disponível |
| Fumaça | Docker | o container não responde em `/health` ou roda como root |

A imagem só é publicada no GHCR depois que todas as etapas passam, e só na branch `main`.
O deploy automático na nuvem entra junto com o Terraform.

## Observabilidade

As quatro métricas de ouro, coletadas em `/metrics` pelo Prometheus e exibidas no Grafana:

| Métrica | Como é medida |
|---|---|
| Latência | p50, p95 e p99 de `http_request_duration_highr_seconds` |
| Tráfego | requisições por segundo, por rota (`http_requests_total`) |
| Erros | percentual de respostas 5xx e 4xx |
| Saturação | requisições simultâneas, CPU e memória do processo |

Alertas em [monitoring/alerts.yml](monitoring/alerts.yml): `AppForaDoAr`, `TaxaDeErrosAlta`, `LatenciaAlta` e `SaturacaoAlta`.

Para ver um alerta disparar: `docker compose stop app`, aguarde cerca de 1 minuto e abra http://localhost:9090/alerts. O `AppForaDoAr` passa a FIRING e aparece no painel "Alertas ativos" do Grafana. `docker compose start app` resolve o alerta.

Para monitorar o MVP publicado a partir da sua máquina, copie `monitoring/targets/producao.yml.example` para `producao.yml` e troque o host.

## Dados pessoais e LGPD

- As duas views da Ouro usadas hoje não têm nome nem e-mail: o funcionário aparece como um hash (`funcionario_chave`).
- O app não usa GPS; trabalha só com estação de embarque e janela de entrada.
- Os dados do repositório são de uma empresa fictícia.
