import {render, h} from 'preact';
import dp from 'dot-prop-immutable';

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

export function hh(tag, pattrs, ...children) {
    var attrs = null
    var child = null
    if (pattrs && (typeof pattrs == 'object') && !Array.isArray(pattrs) && pattrs.props == undefined) {
        attrs = pattrs
    } else {
        child = pattrs
    }
    if ((typeof tag == 'string') && tag.includes('.')) {
        const parts = tag.split('.')
        tag = parts[0]
        attrs = attrs || {}
        attrs['class'] = parts.slice(1).join(' ')
    }
    return h(tag, attrs, child, ...children)
}

const _ids = new WeakMap();
let _idCounter = 1;

export function getObjectId(obj) {
  if (!_ids.has(obj)) {
    _ids.set(obj, _idCounter++);
  }
  return _ids.get(obj);
}

export function fieldModel(signal, path) {
    const value = dp.get(signal.value, path);
    const onInput = (e) => {
        const v = e.currentTarget.value
        signal.value = dp.set(signal.value, path, v)
    }
    return {value, onInput}
}
