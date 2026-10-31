FROM node:22.14.0-alpine3.21 AS build
WORKDIR /workspace
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_GATE_G0_STATUS=unknown
ENV VITE_GATE_G0_STATUS=${VITE_GATE_G0_STATUS}
RUN npm run build

FROM nginx:1.27.5-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/dist /usr/share/nginx/html
EXPOSE 80
