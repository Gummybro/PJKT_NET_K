import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
import { tanstackRouter } from '@tanstack/router-plugin/vite';
import { fileURLToPath } from 'node:url';
export default defineConfig({plugins:[tanstackRouter({target:'react',autoCodeSplitting:false}),react(),tailwind()],resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},server:{proxy:{'/api':'http://127.0.0.1:8787','/monitored':'http://127.0.0.1:8787'}}});
