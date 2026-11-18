# Como cada disciplina se conecta ao MVP

Todas as peças entram pela mesma API. Este documento é o contrato para a equipe: o que cada componente envia, para onde e com qual credencial.

| Disciplina | Componente | Como entra no produto | Tela | Situação |
|---|---|---|---|---|
| Big Data | Views da Ouro | Arquivos CSV em `api/data/`, lidos pela API | Lotação prevista, Minha semana | Integrado com dados reais da Ouro |
| RPA | Robô Python | Contrato `productApiContract.yaml` | Empresa (RH), Alertas | API pronta; falta apontar o robô |
| Visão computacional | YOLO | `POST /api/liveReadings` com `source: "vision"` | Ao vivo | API pronta; falta o envio pelo modelo |
| Maker Lab | ESP32 | `POST /api/liveReadings` com `source: "device"` | Ao vivo | API pronta; falta o envio pelo dispositivo |
| Generative AI | LLM local com RAG | A API repassa a pergunta para `LLM_API_URL` | Pergunte | API pronta; falta o endereço da LLM |
| BI e pitch | Indicadores | `GET /api/hr/dashboard` | Empresa (RH) | Calculado a partir das escalas aprovadas |
| DevOps | Produção | Container, pipeline, Terraform, métricas | `/health`, `/metrics` | No ar |

## Credenciais

Três valores, definidos por variável de ambiente. Nenhum tem padrão: em branco, o grupo de endpoints responde 503.

| Variável | Quem usa | Como envia |
|---|---|---|
| `ROBOT_API_KEY` | Robô RPA | Header `X-Api-Key` |
| `SENSOR_API_KEY` | Visão e ESP32 | Header `X-Api-Key` |
| `HR_ACCESS_CODE` | Pessoa do RH, na tela Empresa | Digitado na tela (header `X-Hr-Code`) |

Em produção, as chaves são geradas na própria VM e ficam em `/opt/foradopico/.env`. Combine a entrega das chaves com cada integrante por um canal privado; nunca no repositório.

## RPA

Os dez endpoints de `productApiContract.yaml` estão implementados na raiz da API, com as regras do handoff: idempotência por `Idempotency-Key`, `dedupeKey` e pela combinação do plano B, `dispatched` por versão e erros no formato `{"errors": [{"field", "message"}]}`.

No `.env` do robô:

```
PRODUCT_API_URL=https://foradopico-gs.brazilsouth.cloudapp.azure.com
PRODUCT_API_KEY=<valor de ROBOT_API_KEY>
```

Diferenças em relação ao mock, para o Matheus conferir:

- Cada `Assignment` traz campos extras (`crowdingIndex`, `baselineEntryWindow`, `baselineCrowding`, `baselineCrowdingIndex`, `remote`), usados pelo painel do RH.
- `predictedCrowding` vem `null` quando a estação não existe na camada Ouro (hoje só Linhas 1 e 3).
- Plano B aprovado altera as escalas cobertas (`remote: true` ou nova `entryWindow`), sem incrementar `version`.
- Ainda não existe edição manual de escala pelo RH (o caso que incrementa `version`).

## Visão computacional e ESP32

```
POST /api/liveReadings
X-Api-Key: <SENSOR_API_KEY>
Content-Type: application/json

{
  "source": "vision",
  "sourceId": "camera-01",
  "stationName": "Corinthians-Itaquera",
  "lineName": "3-Vermelha",
  "peopleCount": 148,
  "densityCategory": "Crítico",
  "capturedAt": "2026-11-17T07:15:00-03:00"
}
```

| Campo | Obrigatório | Observação |
|---|---|---|
| `source` | sim | `vision` (YOLO) ou `device` (ESP32) |
| `sourceId` | sim | Identificador da câmera ou do dispositivo |
| `stationName` | sim | Igual ao nome na camada Ouro, para a comparação com a previsão |
| `lineName` | não | `1-Azul` ou `3-Vermelha`; necessário em estações de integração, como a Sé |
| `peopleCount` | sim | Pessoas contadas |
| `densityCategory` | não | `Vazio`, `Moderado`, `Cheio` ou `Crítico` |
| `capturedAt` | não | ISO 8601; se ausente, vale a hora do recebimento |
| `simulated` | não | `true` para leituras de demonstração |

Resposta: `201`. A tela "Ao vivo" mostra a leitura mais recente de cada fonte por estação, ao lado da previsão para o horário.

Exemplo para o ESP32 (Arduino): `HTTPClient` com `https.addHeader("X-Api-Key", CHAVE)` e o JSON acima com `"source": "device"`.

Este formato é uma proposta minha para destravar a integração. Se o modelo ou o dispositivo já produzem outro formato, o ajuste é na API.

## Generative AI

A API do produto recebe a pergunta em `POST /api/assistant` e repassa para o endereço em `LLM_API_URL`:

```
POST <LLM_API_URL>
{"question": "Posso levar bicicleta no metrô?"}
```

Resposta esperada da LLM:

```
{
  "answer": "Sim, em horários determinados...",
  "refused": false,
  "sources": [{"title": "Regulamento do Metrô, art. 12", "url": "https://..."}]
}
```

- `refused: true` é o caso "não consta": a tela mostra o selo "Não consta na base".
- `sources` aceita objetos `{title, url}` ou só textos.
- Se a LLM estiver fora do ar ou demorar mais de 45 segundos, a tela avisa e o resto do app continua funcionando.

A LLM roda na máquina de quem a treinou, então `LLM_API_URL` precisa ser um endereço que a VM alcance (por exemplo, um túnel). Também é uma proposta de formato: se a API de vocês for diferente, me passem o formato real.

## Demonstração sem os componentes ligados

`scripts/demo_seed.py` envia dados fictícios pelos mesmos endpoints, marcados como simulados:

```
$env:ROBOT_API_KEY="..."; $env:SENSOR_API_KEY="..."
python scripts/demo_seed.py --url http://localhost:8000
```

Rode, aprove a escala em "Empresa (RH)" e rode de novo para o plano B aparecer. No pitch, prefira os componentes reais; o script é o reserva.

## Limites conhecidos do MVP

- Não há login de usuário: "Minha semana" simula o login por um seletor, e o RH entra com um código único.
- "Minha semana" lê a view da Ouro (funcionário identificado por hash), enquanto a área do RH usa as escalas importadas pelo robô. São dois conjuntos de dados sem chave em comum.
- A escala original considera todos entrando às 08:00, por isso o "antes" aparece sempre no pico.
- O motor de escala é uma heurística simples, descrita em `api/app/engine.py`.
