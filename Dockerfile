FROM node:22-alpine AS frontend-build
WORKDIR /build/miniapp
COPY miniapp/package*.json ./
RUN npm install
COPY miniapp/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY bot ./bot
COPY scripts ./scripts
COPY --from=frontend-build /build/miniapp/dist ./miniapp/dist
RUN mkdir -p /app/data
COPY deploy/bothost-entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
EXPOSE 3000
CMD ["/app/entrypoint.sh"]
