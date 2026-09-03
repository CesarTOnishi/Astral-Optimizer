import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  publicDir: false,
  resolve: { tsconfigPaths: true },
  ssr: { noExternal: true },
  build: {
    ssr: true,
    outDir: '.honkai-engine',
    emptyOutDir: true,
    target: 'esnext',
    minify: false,
    sourcemap: false,
    rollupOptions: {
      input: resolve(import.meta.dirname, 'src/honkaiBridge.ts'),
      output: { entryFileNames: 'benchmark-engine.js' },
    },
  },
})
