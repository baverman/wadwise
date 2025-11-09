import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';

export default {
  input: ['preact-all.js'],
  output: {
    dir: '../static/js',
    format: 'es'
  },
  plugins: [nodeResolve(), commonjs()]
};
