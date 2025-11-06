import { nodeResolve } from '@rollup/plugin-node-resolve';

export default {
  input: ['preact-all.js'],
  output: {
    dir: '../static/js',
    format: 'es'
  },
  plugins: [nodeResolve()]
};
