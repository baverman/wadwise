import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';

export default {
  input: ['import_transactions.js', 'settings.js'],
  output: {
    dir: '../static/js',
    format: 'es'
  },
  plugins: [nodeResolve(), commonjs()]
};
