# Development image for the Onus web app (Next.js).
# Dependencies are installed at build time; the source tree is bind-mounted at
# runtime (see docker-compose.yml) so changes hot-reload without a rebuild.
FROM node:20-slim

WORKDIR /app

# Install dependencies from the lockfile first for better layer caching.
COPY package.json package-lock.json* ./
RUN npm install

EXPOSE 3000

# docker-compose overrides this to bind 0.0.0.0:3000; this is a sensible default.
CMD ["npm", "run", "dev"]
