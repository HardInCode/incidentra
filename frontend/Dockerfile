FROM node:18-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
# ajv@8 di devDependencies + lockfile = build react-scripts stabil di Docker
RUN npm ci --legacy-peer-deps

COPY . .

ARG REACT_APP_API_URL=http://localhost:5000/api
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV DISABLE_ESLINT_PLUGIN=true
ENV CI=true
ENV GENERATE_SOURCEMAP=false
ENV NODE_OPTIONS=--max-old-space-size=4096

RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
# nginx:alpine's default entrypoint runs envsubst on *.template files in
# /etc/nginx/templates/ before starting nginx, substituting ${PORT}. PaaS platforms like
# Railway inject a dynamic PORT at runtime; ENV PORT=80 below keeps local Docker Compose
# (which maps host 3000 -> container 80, and never sets PORT) working unchanged.
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV PORT=80
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
