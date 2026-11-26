FROM node:26.13.0-alpine AS frontend
WORKDIR /frontend
RUN npm install --global pnpm@10.16.1
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.15.2-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend/dist
RUN useradd --create-home --uid 10001 dove && mkdir -p /data/objects && chown -R dove:dove /data /app
USER dove
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "dove.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
