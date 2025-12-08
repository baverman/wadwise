import { nodeResolve } from '@rollup/plugin-node-resolve'
import { globSync } from 'glob'
import preact from '@preact/preset-vite'
import tailwindcss from '@tailwindcss/vite'
import eslint from 'vite-plugin-eslint'

const pages = globSync('src/page/*.js')
const styles = globSync('src/styles/*.css')

export default {
    plugins: [eslint(), tailwindcss(), preact()],
    server: { cors: { origin: 'http://127.0.0.1:5000' } },
    build: {
        outDir: 'static/assets',
        assetsDir: '.',
        emptyOutDir: true,
        manifest: true,
        rollupOptions: {
            input: [...pages, ...styles],
            // output: { format: 'es', chunkFileNames: 'chunk-[hash].js' },
            plugins: [nodeResolve()],
            preserveEntrySignatures: 'allow-extension',
        },
    },
}
