# Como cada disciplina se conecta ao MVP

Todas as peças entram pela mesma API. Este documento diz o que cada componente envia, para onde e com qual credencial. Os formatos foram conferidos contra o código de cada repositório.

| Disciplina | Componente | Como entra no produto | Tela | Testado contra |
|---|---|---|---|---|
| Big Data | Views da Ouro | CSV exportado em `api/data/`, lido pela API | Lotação prevista, Minha semana | CSV idêntico ao do repositório de Generative AI |
| RPA | Robô `SemestralRpa` | Contrato `productApiContract.yaml` | Empresa (RH), Alertas | O próprio robô: importação, aprovação, envio, falha simulada, plano B |
| Visão computacional | `demo_tempo_real.py` (YOLO11) | `POST /api/liveReadings`, `source: "vision"` | Ao vivo | Módulo de envio rodando contra a API |
| Maker Lab | Carrinho ESP32 (LDR, DHT11, Gemini) | `POST /api/liveReadings`, `source: "device"` | Ao vivo | JSON gerado pelo código do ESP32 compilado com g++ (sem a placa) |
| Generative AI | API `POST /perguntar` | A API repassa a pergunta para `LLM_API_URL` | Pergunte | API real da equipe, com o modelo substituído por respostas fixas |
| BI e pitch | Indicadores | `GET /api/hr/dashboard` | Empresa (RH) | Testes automatizados |
| DevOps | Produção | Container, pipeline, Terraform, métricas | `/health`, `/metrics` | Em produção |

## Credenciais

Três valores, definidos por variável de ambiente. Nenhum tem padrão: em branco, o grupo de endpoints responde 503.

| Variável | Quem usa | Como envia |
|---|---|---|
| `ROBOT_API_KEY` | Robô RPA | Header `X-Api-Key` (no robô: `PRODUCT_API_KEY`) |
| `SENSOR_API_KEY` | Câmera e ESP32 | Header `X-Api-Key` (na câmera: `FORADOPICO_SENSOR_KEY`; no ESP32: `FORADOPICO_API_KEY` no `secrets.h`) |
| `HR_ACCESS_CODE` | Pessoa do RH, na tela Empresa | Digitado na tela |

Em produção, as chaves são geradas na própria VM e ficam em `/opt/foradopico/.env`. Passe cada chave por canal privado; nunca no repositório, no `secrets.h` versionado ou em print.

## RPA

Os dez endpoints do contrato estão na raiz da API, com idempotência por `Idempotency-Key`, `dedupeKey` e pela combinação do plano B, `dispatched` por versão e erros no formato `{"errors": [{"field", "message"}]}`.

No `.env` do robô:

```
PRODUCT_API_URL=https://foradopico-gs.brazilsouth.cloudapp.azure.com
PRODUCT_API_KEY=<valor de ROBOT_API_KEY>
```

Ou rode o robô na própria VM com `infra/robo-na-vm.sh`: ele usa o endereço interno `http://app:8000`.

Diferenças em relação ao mock, todas compatíveis com o robô:

- Cada escala traz campos extras (`crowdingIndex`, `baselineEntryWindow`, `baselineCrowding`, `baselineCrowdingIndex`, `remote`), que o robô ignora.
- `predictedCrowding` vem `null` quando a estação não existe na camada Ouro (só há Linhas 1 e 3).
- Plano B aprovado altera as escalas cobertas (`remote: true` ou nova `entryWindow`) sem incrementar `version`.
- Ainda não existe edição manual de escala pelo RH (o caso que incrementa `version`).

## Visão computacional

O script `demo_tempo_real.py` ganhou opções para enviar a contagem ao app. O envio roda numa thread separada: o vídeo não espera a rede. Só números saem da máquina; as cabeças continuam borradas e nenhuma imagem é enviada.

```
$env:FORADOPICO_SENSOR_KEY="<SENSOR_API_KEY>"
python demo_tempo_real.py --modelo modelo/best.pt --fonte video.mp4 `
  --api-url https://foradopico-gs.brazilsouth.cloudapp.azure.com `
  --estacao "Corinthians-Itaquera" --linha 3-Vermelha --camera camera-01
```

Sem `--api-url`, o script funciona como antes. O rodapé do vídeo mostra quantos envios deram certo ou o último erro.

Formato enviado a cada 5 segundos (`--intervalo-envio`):

```json
{"source": "vision", "sourceId": "camera-01", "stationName": "Corinthians-Itaquera",
 "lineName": "3-Vermelha", "peopleCount": 37, "capacity": 40, "crowdingIndex": 0.925,
 "densityCategory": "Critico", "capturedAt": "2026-11-18T07:15:00-03:00"}
```

A API aceita "Critico" sem acento, como o script escreve. Use o nome da estação igual ao da camada Ouro, para a tela comparar a medição com a previsão.

## Maker Lab

O robô-sensor **não conta pessoas**: ele envia luz, classificação da iluminação, temperatura, umidade, trecho escuro, total de ocorrências e o último texto devolvido pelo Gemini.

A integração é o arquivo novo `foradopico_api.h` e duas mudanças no `.ino` (o `#include` e a chamada `foradopicoLoop()` no fim do `loop()`). Ela só liga se o `secrets.h` tiver:

```
#define ESTACAO_NOME       "Corinthians-Itaquera"
#define FORADOPICO_API_URL "https://foradopico-gs.brazilsouth.cloudapp.azure.com"
#define FORADOPICO_API_KEY "<SENSOR_API_KEY>"
```

Sem essas linhas, o carrinho funciona exatamente como antes. O envio acontece a cada 10 segundos ou logo que o trecho escuro começa, termina ou chega um texto novo da IA, e **só com o carrinho parado**: a chamada de rede trava o loop por até alguns segundos, e em movimento o carrinho precisa continuar lendo o LDR para parar no trecho escuro.

Formato:

```json
{"source": "device", "sourceId": "esp32-carrinho-01", "stationName": "Corinthians-Itaquera",
 "lightPct": 14, "lightClass": "critica", "temperatureC": 29.5, "humidityPct": 72,
 "darkZone": true, "darkZoneCount": 2, "aiAlert": "Trecho escuro na plataforma..."}
```

## Generative AI

A API do produto recebe a pergunta em `POST /api/assistant` e repassa para `POST <LLM_API_URL>/perguntar`, o contrato do repositório de Generative AI:

```
{"pergunta": "Quantas pessoas entram na Sé na segunda às 18h?"}
-> {"pergunta": "...", "resposta": "...", "fontes": ["lot-se-segunda-l1"], "recusou": false, "confianca": 1.0}
```

- `recusou: true` aparece na tela como "Fora da cobertura: não consta na base".
- O tempo limite é de 90 segundos, porque o modelo roda localmente.
- Se o assistente estiver fora do ar, a tela avisa e o resto do app continua funcionando.

O assistente precisa do Ollama com `llama3.1:8b` e `bge-m3`, então roda numa máquina com GPU, não na VM. Para a demonstração:

1. Na máquina com o Ollama, suba a API do assistente na porta 8010 (a 8000 é do app):
   ```
   uvicorn api.main:app --port 8010
   ```
2. No `.env` do ForaDoPico: `LLM_API_URL=http://host.docker.internal:8010`.
3. Suba o app com `docker compose up --build` e abra `http://localhost:8000/#assistente`.

Na URL pública, a tela "Pergunte" mostra que o assistente não está conectado. Para ligar na nuvem seria preciso expor a máquina do Ollama com um túnel, o que fica como próximo passo.

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
- A escala original considera todos entrando às 08:00, por isso o "antes" aparece quase sempre no pico.
- O motor de escala é uma heurística simples, descrita em `api/app/engine.py`.
- O robô-sensor mede o ambiente, não a lotação; a relação entre calor e lotação é uma hipótese, como diz o próprio repositório do Maker Lab.
