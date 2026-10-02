# Imaginea "web": aplicatia Flutter la /, panoul operatorului (React) la /admin/, ambele servite de nginx,
# care trimite /api/ mai departe la containerul api. Contextele "mobile" si "admin" vin din docker-compose.yml.
# Imaginea cirruslabs nu are tag pentru Flutter 3.47, de aceea "stable"; alta versiune se alege cu
#   docker compose build --build-arg FLUTTER_IMAGE=ghcr.io/cirruslabs/flutter:<versiune> web
ARG FLUTTER_IMAGE=ghcr.io/cirruslabs/flutter:stable

FROM ${FLUTTER_IMAGE} AS flutter-build
WORKDIR /src
COPY --from=mobile pubspec.yaml pubspec.lock ./
RUN flutter pub get
COPY --from=mobile . .
ARG API_URL=
ARG WEATHER_API_KEY=
# --wasm also builds the JavaScript version; flutter_bootstrap.js picks one per browser
RUN flutter build web --release --wasm \
    --dart-define=API_URL=${API_URL} \
    --dart-define=WEATHER_API_KEY=${WEATHER_API_KEY}

FROM node:24-alpine AS admin-build
WORKDIR /src
COPY --from=admin package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY --from=admin index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY --from=admin public ./public
COPY --from=admin src ./src
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=flutter-build /src/build/web /usr/share/nginx/html
COPY --from=admin-build /src/dist /usr/share/nginx/html/admin
EXPOSE 80
