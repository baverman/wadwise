import { h } from 'preact'

export function _hh(tag, pattrs, ...children) {
    // console.log(tag, pattrs, children)
    var attrs = null
    var child = null
    if (
        pattrs &&
        typeof pattrs == 'object' &&
        !Array.isArray(pattrs) &&
        pattrs.props == undefined
    ) {
        attrs = pattrs
    } else {
        child = pattrs
    }
    if (typeof tag == 'string' && tag.includes('.')) {
        const parts = tag.split('.')
        tag = parts[0]
        attrs = attrs || {}
        attrs['class'] = parts.slice(1).join(' ')
    }
    return h(tag, attrs, child, ...children)
}

const tagHandler = {
    get(target, tag) {
        const key = 'tag-' + tag
        if (key in target) {
            return target[key]
        }
        const v = (target[key] = new Proxy((...args) => _hh(tag, ...args), classHandler))
        v._wadwise_tag = tag
        return v
    },
}

const classHandler = {
    get(target, cls) {
        const key = 'cls-' + cls
        if (key in target) {
            return target[key]
        }
        const newtag = target._wadwise_tag + '.' + cls
        const v = (target[key] = new Proxy((...args) => _hh(newtag, ...args), classHandler))
        v._wadwise_tag = newtag
        return v
    },
}

export const nbsp = '\xA0'
export const hh = new Proxy(_hh, tagHandler)
