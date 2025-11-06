import {render, h} from 'preact';

window._wadwiseFuncs = {}

export function registerPreactData(fn) {
    window._wadwiseFuncs[fn.name] = fn
}

export function initPreactData() {
    for (const el of document.querySelectorAll('[data-preact]')) {
        render(h(window._wadwiseFuncs[el.dataset.preact]), el);
    }
}

export function idify(data) {
    data.forEach(it => {it.id = crypto.randomUUID()})
    return data;
}

const getAttributes = (element) => {
  const attributes = {};
  for (let attr of element.attributes) {
    attributes[attr.name] = attr.value;
  }
  return attributes;
};

const toVNodeTree = (childNodes) => {
  const tree = [];
  childNodes.forEach((node) => {
    if (node.nodeType === 3) {
      return tree.push(node.data);
    }
    if (node.nodeType === 1) {
      return tree.push(
        h(node.nodeName.toLowerCase(), getAttributes(node), toVNodeTree(node.childNodes))
      );
    }
  });
  return tree;
};

export const node2component = (element) => h(element.nodeName.toLowerCase(), getAttributes(element), toVNodeTree(element.childNodes));
