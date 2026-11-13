FROM node:22-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914 AS build
WORKDIR /app
COPY package*.json ./
# Vite 8's native dependencies (including musl builds) are in the lockfile.
RUN npm ci --include=optional
COPY . .
# Firebase web configuration is public and compiled into both app and worker.
# Pass these build args through Compose; no service-account secret belongs here.
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
ARG VITE_FIREBASE_VAPID_KEY
ARG VITE_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000
RUN npm run build

FROM nginx:1.29-alpine3.23@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Refresh the Alpine security repository at image-build time so the runtime
# image receives fixes released after the base image tag was published.
RUN apk upgrade --no-cache

# nginx:alpine ships an `nginx` user and an unprivileged image variant, but a
# stock image still starts its master process as root to bind port 80. Rather
# than re-architect the port, drop the master to the shipped unprivileged user
# and give it only the paths it writes at runtime (cache, pid, logs). Static
# assets stay root-owned and read-only to the server process.
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /usr/share/nginx/html \
 && touch /var/run/nginx.pid \
 && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080
CMD ["sh", "-c", "envsubst '${S3_PUBLIC_ENDPOINT_URL} ${CSP_UPGRADE_INSECURE}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
