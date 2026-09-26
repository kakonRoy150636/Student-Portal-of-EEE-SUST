FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
# npm ci cannot install @rollup/rollup-linux-x64-musl on alpine.
#
# The cause is not "--include=optional" (the flag below already did that):
# package-lock.json carries a resolvable entry for the *gnu* binary
# ("node_modules/@rollup/rollup-linux-x64-gnu", line ~1556) but has NO
# entry at all for the musl one, even though rollup's optionalDependencies
# list names it. npm ci installs strictly from lockfile entries, so on
# alpine the musl binary can never arrive and vite dies with
# "Cannot find module @rollup/rollup-linux-x64-musl".
#
# Regenerating the lockfile on a glibc host does not help, because the
# host is glibc and again never materialises a musl entry. So install the
# platform binary explicitly after the normal install.
RUN npm ci --include=optional \
 && npm install --no-save --force @rollup/rollup-linux-x64-musl@4.63.2
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# নতুন nginx.conf কন্টেইনারে কপি করার লাইন
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
