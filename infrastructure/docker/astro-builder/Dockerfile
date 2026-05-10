FROM node:22-slim

RUN apt-get update -qq && apt-get install -y -qq wget curl && \
    wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc && \
    npx --yes create-astro@latest /astro-template --template basics --no-install --no-git --yes && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
