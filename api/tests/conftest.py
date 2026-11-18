import os
import secrets

# Banco em memória e chaves aleatórias, definidos antes de a aplicação ser importada.
os.environ["DB_PATH"] = ":memory:"
for name in ("ROBOT_API_KEY", "SENSOR_API_KEY", "HR_ACCESS_CODE"):
    os.environ[name] = secrets.token_hex(16)
os.environ.pop("LLM_API_URL", None)
