# This Dockerfile is ONLY for the frontend development server.
# We will NOT use a second stage.
FROM node:18-alpine

WORKDIR /app

# Copy package files and install dependencies
# This step is important to create a base image with all node_modules
COPY package.json package-lock.json* ./
RUN npm ci

# Copy the rest of the source files. The volume mount will keep them up-to-date.
COPY . .

# We don't need to run `npm run build` here for the dev server.
# The 'command' in the compose file will handle what runs.
