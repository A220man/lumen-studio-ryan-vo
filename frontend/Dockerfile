FROM node:24-alpine AS builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --frozen-lockfile
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
LABEL org.opencontainers.image.authors="Ryan Vo <ryandtvo@gmail.com>"
LABEL org.opencontainers.image.title="lumen-studio-frontend"

# Run as nonroot nginx user (provided by base image).
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d

COPY --from=builder /build/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO /dev/null http://127.0.0.1:80/ || exit 1

EXPOSE 80
USER nginx
CMD ["nginx", "-g", "daemon off;"]