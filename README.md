# ForaDoPico

Escala presencial inteligente para quem usa trem e metrô no horário de pico.
Global Solution FIAP 2026.2 · CitizenTech · Engenharia de Software 4ES.

## Integrantes

| Nome completo | RM |
|---|---|
| João Pedro Saborido Silva | 98184 |
| Matheus Haruo Queiroz Omori | 97663 |
| Pedro Guerra de Souza Freitas | 99526 |
| Victor Augusto Wittner | 98667 |

## Ficha Técnica do MVP

| Campo | Descrição |
|---|---|
| **Nome do produto** | ForaDoPico |
| **Cidadão e território** | Trabalhador CLT que usa trem e metrô no horário de pico na Grande São Paulo |
| **Problema, em uma frase** | Escalas presenciais montadas sem olhar o transporte jogam todo mundo no mesmo dia e horário, justamente no pico |
| **Proposta de valor** | Viaje fora do aperto: saiba quando sair para pegar o trem mais vazio, e ajude a cidade a respirar no horário de pico |
| **Arquitetura: componentes** | API (FastAPI) e front (React) na mesma imagem, numa VM Azure; pipeline de dados (Airflow e Databricks); robô RPA (Python, BotCity); visão computacional (YOLO11); assistente de lotação (LLM local com RAG e ferramenta); robô-sensor de estação (ESP32) |
| **Fontes de dados** | Demanda por estação do portal de transparência do Metrô de SP; clima do Open-Meteo; feriados da BrasilAPI; situação das linhas no site do Metrô (robô RPA); planilha de escala do RH; contagem pela câmera; luz, temperatura e umidade do robô-sensor. O app lê as views da Ouro `vw_app_lotacao_prevista` e `vw_app_minha_semana` |
| **Modelos de IA utilizados** | YOLO11n com fine-tuning para detectar cabeças (contagem de pessoas, MAE 3,6); `llama3.1:8b` e `bge-m3` locais via Ollama (assistente com RAG e ferramenta); Gemini no robô-sensor (alerta e relatório da ronda) |
| **URL do MVP e repositório** | URL: https://foradopico-gs.brazilsouth.cloudapp.azure.com · Repositório: este |
| **Indicadores de impacto** | Horas devolvidas ao funcionário por mês; viagens no pico evitadas por funcionário; lotação média evitada; dias com plano B acionado |
| **ODS conectados** | ODS 11 (cidades sustentáveis), ODS 3 (saúde e bem-estar), ODS 9 (inovação e infraestrutura), ODS 10 (redução das desigualdades) |

Repositórios das outras disciplinas: [Big Data](https://github.com/saborido613/foradopico-bigdata) · [RPA](https://github.com/haruoooo/SemestralRpa) · [Generative AI](https://github.com/lucca0100/ForaDoPico) · Visão computacional: A PREENCHER · Maker Lab: A PREENCHER.

## O que o MVP faz

| Tela | O que mostra | De onde vem |
|---|---|---|
| Lotação prevista | Lotação por estação, dia e faixa de 15 min, com o melhor horário | Big Data: `vw_app_lotacao_prevista` (Ouro · Databricks) |
| Minha semana | Dias presenciais, janela sugerida e antes × depois | Big Data: `vw_app_minha_semana` (Ouro · Databricks) |
| Alertas | Situação das linhas, falhas e plano B aprovado | RPA: robô monitorando o site do Metrô, pelo contrato da API |
| Ao vivo | Pessoas na plataforma medidas pela câmera, ao lado da previsão; luz, temperatura, umidade e alerta da IA do robô-sensor | Visão computacional (YOLO11) e Maker Lab (ESP32) |
| Pergunte | Lotação prevista, pico e melhor horário em linguagem natural, com fonte ou "não consta" | Generative AI: assistente local com RAG e ferramenta |
| Empresa (RH) | Aprovação de escalas e planos B, indicadores de impacto e negócio | RPA, motor de escala e BI |

O contrato de cada integração está em [docs/integracao.md](docs/integracao.md). Operação: `GET /health`, `GET /metrics` (Prometheus) e documentação interativa em `/api/docs`.

## Como rodar

Pré-requisito: Docker com Docker Compose.

```bash
cp .env.example .env      # troque a senha do Grafana e gere as chaves do MVP
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
api/          API FastAPI, dados da Ouro, motor de escala e testes
scripts/      Dados fictícios de demonstração
web/          Front React (Vite)
monitoring/   Prometheus, regras de alerta e dashboard do Grafana
infra/        Terraform da nuvem
docs/         Contratos de integração (robô RPA, visão, ESP32 e assistente)
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

**Deploy automático:** a VM confere o GHCR a cada minuto e troca o container quando há imagem nova. O job `deploy` só fica verde quando `/health` na URL pública responde com a versão do commit. Nenhuma credencial da Azure fica no GitHub, e a porta 22 não precisa aceitar os runners.

## Infraestrutura (Terraform, Azure)

`infra/` cria: grupo de recursos, rede virtual, NSG, IP público com DNS e uma VM Ubuntu que sobe o app atrás do Caddy (HTTPS automático).

| Porta | Origem | Motivo |
|---|---|---|
| 443 e 80 | Internet | O MVP é público; a 80 só redireciona e valida o certificado |
| 22 | Somente `admin_cidr` (seu IP /32) | Administração. A variável recusa `/0` na validação |

```bash
az login
cd infra
cp terraform.tfvars.example terraform.tfvars   # preencha; o arquivo é ignorado pelo git
terraform init
terraform plan
terraform apply
```

O state (`*.tfstate`) e o `terraform.tfvars` ficam fora do repositório. Depois do apply, grave a saída `url_do_mvp` na variável `MVP_URL` do repositório (Settings → Secrets and variables → Actions → Variables) e deixe o pacote da imagem no GHCR como público.

Para destruir tudo e parar a cobrança: `terraform destroy`.

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

- As duas views da Ouro não têm nome nem e-mail: o funcionário aparece como um hash (`funcionario_chave`).
- A planilha do RH traz nome, e-mail, time e estação de embarque. Esses dados ficam só no banco da API (SQLite em volume da VM) e só saem por endpoints autenticados (robô e RH). As telas públicas não mostram nenhum deles.
- O app não usa GPS; trabalha só com estação de embarque e janela de entrada.
- Os logs e as métricas não registram dados pessoais.
- Os dados de demonstração são de uma empresa fictícia.
- As chaves de acesso são geradas na VM e nunca passam pelo repositório nem pelo estado do Terraform.
