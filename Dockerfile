FROM node:22.19.0-alpine AS frontend
WORKDIR /frontend
RUN corepack enable && corepack prepare pnpm@10.16.1 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend/dist
RUN useradd --create-home --uid 10001 dove && mkdir -p /data/objects && chown -R dove:dove /data /app
USER dove
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "dove.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
