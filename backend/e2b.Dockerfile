FROM e2bdev/code-interpreter:latest 

# Set working directory
WORKDIR /home/user

RUN apt-get update && apt-get install -y tree
# Install Vite (React template) and TailwindCSS
RUN npm create vite@5.2.1 react-app -- --template react && \
    cd react-app && \
    npm install

WORKDIR /home/user/react-app

RUN echo "import { defineConfig } from 'vite'\nimport react from '@vitejs/plugin-react'\n\nexport default defineConfig({\n  plugins: [react()],\n \n  }\n})" > vite.config.js
