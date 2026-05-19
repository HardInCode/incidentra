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
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
