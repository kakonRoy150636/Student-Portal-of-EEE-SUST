FROM node:26-alpine AS build
WORKDIR /app
COPY package*.json ./
# Vite 8's native dependencies (including musl builds) are in the lockfile.
RUN npm ci --include=optional
COPY . .
RUN npm run build

FROM nginx:1.29-alpine3.23
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

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
CMD ["nginx", "-g", "daemon off;"]
