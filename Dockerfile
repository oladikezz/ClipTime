FROM node:22-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv ffmpeg git build-essential libcairo2-dev libpango1.0-dev \
    libjpeg-dev libgif-dev librsvg2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

RUN git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git vendor/bgutil-ytdlp-pot-provider \
    && cd vendor/bgutil-ytdlp-pot-provider/server \
    && npm ci \
    && npx tsc

RUN python3 -m venv /opt/cliptime-venv \
    && /opt/cliptime-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/cliptime-venv/bin/pip install --no-cache-dir -r backend/requirements.txt

RUN npm run build && chmod +x docker-entrypoint.sh

ENV PATH="/opt/cliptime-venv/bin:$PATH"
ENV NODE_ENV=production
ENV BACKEND_PORT=8765
ENV API_INTERNAL_URL=http://127.0.0.1:8765

EXPOSE 3000
CMD ["./docker-entrypoint.sh"]
