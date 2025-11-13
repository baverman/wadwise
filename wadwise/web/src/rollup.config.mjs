import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';

export default {
  input: ['import_transactions.js', 'settings.js', 'account_view.js'],
  output: {
    dir: '../static/js',
    format: 'es',
    chunkFileNames: 'chunk-[hash].js',
  },
  plugins: [nodeResolve(), commonjs()]
};
