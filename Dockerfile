FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY packages/dysub-core /app/packages/dysub-core
COPY packages/dysub-input-local /app/packages/dysub-input-local
COPY packages/dysub-input-douyin /app/packages/dysub-input-douyin
COPY apps/webui /app/apps/webui

RUN pip install /app/packages/dysub-core[dev] \
    && pip install /app/packages/dysub-input-local \
    && pip install /app/packages/dysub-input-douyin \
    && pip install /app/apps/webui

ENV DYSUB_ASR_API_KEY=""
EXPOSE 7860

CMD ["dysub", "webui", "--host", "127.0.0.1", "--port", "7860"]
