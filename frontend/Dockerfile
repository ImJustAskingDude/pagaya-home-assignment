FROM node:22-slim

ARG UID=1000
ARG GID=1000

ENV NPM_CONFIG_CACHE=/tmp/.npm

WORKDIR /app

RUN chown "${UID}:${GID}" /app
COPY --chown=${UID}:${GID} package.json package-lock.json ./
USER ${UID}:${GID}
RUN npm ci

USER root
COPY --chown=${UID}:${GID} . .
USER ${UID}:${GID}

CMD ["npm", "run", "dev"]
