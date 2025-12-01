FROM node:20-alpine AS build
WORKDIR /app
COPY client/package*.json /app/
RUN npm ci
COPY client /app
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY server/client.nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


