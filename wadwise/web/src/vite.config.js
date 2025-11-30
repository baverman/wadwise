import { nodeResolve } from '@rollup/plugin-node-resolve'
import preact from '@preact/preset-vite'
import tailwindcss from '@tailwindcss/vite'
import eslint from 'vite-plugin-eslint'

export default {
    plugins: [eslint(), tailwindcss(), preact()],
    server: { cors: { origin: 'http://127.0.0.1:5000' } },
    build: {
        outDir: '../static/assets',
        assetsDir: '.',
        emptyOutDir: true,
        manifest: true,
        rollupOptions: {
            input: [
                'import_transactions.js',
                'settings.js',
                'account_view.js',
                'transaction_edit.js',
            ],
            // output: { format: 'es', chunkFileNames: 'chunk-[hash].js' },
            plugins: [nodeResolve()],
            preserveEntrySignatures: 'allow-extension',
        },
    },
}
