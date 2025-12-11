import js from '@eslint/js'
import globals from 'globals'
import { defineConfig } from 'eslint/config'
import pluginImport from 'eslint-plugin-import'

export default defineConfig([
    {
        files: ['src/**/*.{js,mjs,cjs}'],
        plugins: { js },
        extends: ['js/recommended', pluginImport.flatConfigs.recommended],
        languageOptions: { globals: globals.browser, ecmaVersion: 'latest' },
        rules: { 'no-unused-vars': 'warn' },
    },
])
