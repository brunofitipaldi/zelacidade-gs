# Imagem do app ZelaCidade (Streamlit + visão computacional + assistente).
#
# Construir e rodar:
#   docker build -t zelacidade .
#   docker run -p 8501:8501 zelacidade
# Depois abra http://localhost:8501
#
# Para enviar e-mails de verdade pelo RPA, passe as variáveis ZELA_SMTP_* com -e
# (nunca coloque senha neste arquivo).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TORCH_HOME=/app/.torch

WORKDIR /app

# Dependências primeiro, para o Docker reaproveitar essa camada quando só o código mudar.
# PyTorch da versão só CPU (bem menor que a com CUDA).
COPY requirements.txt .
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY . .

# Baixa os pesos da MobileNetV3 durante o build: o container sobe sem precisar de internet.
RUN python -c "from torchvision import models; models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)"

# Popula o banco com os chamados simulados (data/deteccoes_exemplo.csv) pelo robô de RPA.
RUN python rpa/rpa_chamados.py

# Roda sem privilégio de root.
RUN useradd --create-home zela && chown -R zela /app
USER zela

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
