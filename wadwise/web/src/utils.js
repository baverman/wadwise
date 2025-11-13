import {render, h} from 'preact';

window._wadwiseFuncs = {}

export function registerPreactData(fn) {
    window._wadwiseFuncs[fn.name] = fn
}

export function initPreactData(props) {
    props = props ?? {};
    for (const el of document.querySelectorAll('[data-preact]')) {
        const name = el.dataset.preact
        render(h(window._wadwiseFuncs[name], props[name] || null), el);
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
window._h_render_count = 0;

export function getObjectId(obj) {
  if (!_ids.has(obj)) {
    _ids.set(obj, _idCounter++);
  }
  return _ids.get(obj);
}

export function fieldModel(signal) {
    const onInput = (e) => {
        const v = e.currentTarget.value
        signal.value = v
    }
    return {value: signal, onInput}
}

export function deleteIdx(arr, idx) {
    const v = arr.slice()
    v.splice(idx, 1)
    return v
}

export function deleteIdxSignal(signal, idx) {
    signal.value = deleteIdx(signal.value, idx)
}

export function pushSignal(signal, value) {
    signal.value = [...signal.value, value]
}

export function preventDefault(fn) {
    return (e) => {
        e.preventDefault()
        fn()
    }
}

export function urlqs(base, params) {
    if (!params) {
        return base
    }
    return base + '?' + (new URLSearchParams(params ?? {})).toString()
}

export const nbsp = '\xA0'

export function join(sep, arr) {
    const result = []
    for(const it of arr) {
        if (it !== null && it !== undefined && it !== false) {
            result.push(it)
            result.push(sep)
        }
    }
    if (result.length) {
        result.pop()
    }
    return result
}
