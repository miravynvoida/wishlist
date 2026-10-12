FROM node:22-alpine AS frontend-build
WORKDIR /build/miniapp
COPY miniapp/package*.json ./
RUN npm install
COPY miniapp/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MINIAPP_DIST=/opt/miniapp/dist
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY bot ./bot
COPY scripts ./scripts
COPY --from=frontend-build /build/miniapp/dist /opt/miniapp/dist
RUN mkdir -p /app/data
# Keep the entrypoint outside /app: Bothost may mount the Git repository over /app.
COPY deploy/bothost-entrypoint.sh /usr/local/bin/bothost-entrypoint.sh
RUN chmod +x /usr/local/bin/bothost-entrypoint.sh
EXPOSE 3000
CMD ["/usr/local/bin/bothost-entrypoint.sh"]
