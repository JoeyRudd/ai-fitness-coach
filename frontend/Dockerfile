# Frontend Dockerfile using multi-stage build
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* frontend/pnpm-lock.yaml* ./
RUN npm ci || npm install
COPY frontend .
RUN npm run build

FROM nginx:alpine
# Copy Vite build to Nginx html
COPY --from=build /app/dist /usr/share/nginx/html
# Basic Nginx config for SPA routing
RUN printf 'server {\n  listen 80;\n  server_name _;\n  root /usr/share/nginx/html;\n  location / { try_files $uri /index.html; }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
