import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  resolve: {
    alias: { '@': fileURLToPath(new URL('.', import.meta.url)) },
  },
  test: {
    include: ['testes/**/*.test.ts'],
    // O banco em memória leva alguns segundos para subir com as migrations.
    testTimeout: 30_000,
    hookTimeout: 120_000,
    // Os testes de datas assumem o servidor em UTC, como na Vercel.
    env: { TZ: 'UTC' },
  },
})
