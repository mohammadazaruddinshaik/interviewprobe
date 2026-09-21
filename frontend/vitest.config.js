import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Default environment is plain node: most tests exercise the reducer/
// selectors (pure functions) and the provider adapters (which each stub a
// minimal fake `window` themselves) — no DOM needed. Component tests that
// render React trees opt into jsdom individually via a
// `// @vitest-environment jsdom` docblock at the top of the file, so adding
// them never slows down or risks the plain-function tests.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
    include: ['src/**/*.test.{js,jsx}'],
  },
})
