FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Proxy /api to the backend service inside the compose network.
RUN printf 'server { listen 80; location /api/ { proxy_pass http://api:8123; } location / { root /usr/share/nginx/html; try_files $$uri /index.html; } }\n' > /etc/nginx/conf.d/default.conf
