import { h } from 'preact'
import classNames from 'classnames'

function parseSelector(selector) {
    const [head, ...tail] = selector.trim().split('[')
    let tags = []
    let attrs = null

    if (head) {
        tags = head.split('.')
        const idIdx = tags.findIndex((it) => it[0] == '#')
        if (~idIdx) {
            attrs = { id: tags[idIdx].slice(1) }
            tags.splice(idIdx, 1)
        }
    }

    if (tail.length) {
        attrs = attrs ?? {}
        for (const it of tail) {
            const [name, value] = it.slice(0, -1).split('=', 2)
            attrs[name] = value === undefined ? true : value
        }
    }

    return [tags, attrs]
}

function splitArgs(args) {
    const first = args[0]
    if (first && typeof first == 'object' && !Array.isArray(first) && first.props == undefined) {
        return [first, args.slice(1)]
    }
    return [null, args]
}

function setAttrs(attrs) {
    const pctx = this._wadwise_ctx
    if (typeof attrs === 'function') {
        const ctx = { ...pctx, cache: new Map() }
        const el = createProxy(ctx, classHandler)
        const entries = attrs(el)
        for (const k in entries) {
            ctx.cache.set(k, entries[k])
        }
        return el
    }

    const ctx = { ...pctx, cache: new Map(), attrs: { ...(pctx.attrs ?? {}), ...attrs } }
    return createProxy(ctx, classHandler)
}

function createProxy(ctx, handler) {
    const target = (...args) => {
        let [attrs, children] = splitArgs(args)
        let needNew = true
        if (ctx.attrs) {
            attrs = { ...ctx.attrs, ...(attrs ?? {}) }
            needNew = false
        }

        if (ctx.classList || attrs?.['class']) {
            const clsStr = classNames(ctx.classList, attrs?.['class'])
            if (needNew || !attrs) {
                attrs = { ...(attrs ?? {}), class: clsStr }
            } else {
                attrs['class'] = clsStr
            }
            needNew = false
        }
        return h(ctx.tag, attrs, ...children)
    }
    target._wadwise_ctx = ctx
    ctx.cache.set('$', setAttrs.bind(target))
    return new Proxy(target, handler)
}

function _hh(tag, ...args) {
    const [attrs, children] = splitArgs(args)
    return h(tag, attrs, ...children)
}

_hh._wadwise_ctx = { cache: new Map() }

const tagHandler = {
    get(target, selector) {
        const cache = target._wadwise_ctx.cache
        let value = cache.get(selector)
        if (value !== undefined) {
            return value
        }
        const [tags, attrs] = parseSelector(selector)
        const [tag, ...clsList] = tags
        value = createProxy({ tag, cache: new Map(), clsList, attrs }, classHandler)
        cache.set(selector, value)
        return value
    },
}

const classHandler = {
    get(target, selector) {
        const pctx = target._wadwise_ctx
        const cache = pctx.cache
        let value = cache.get(selector)
        if (value != undefined) {
            return value
        }
        const [clsList, attrs] = parseSelector(selector)
        const ctx = {
            ...pctx,
            cache: new Map(),
            classList: [...(pctx.classList ?? []), ...clsList],
            attrs: attrs ? { ...(pctx.attrs ?? {}), ...attrs } : pctx.attrs,
        }
        value = createProxy(ctx, classHandler)
        cache.set(selector, value)
        return value
    },
}

export function wrapComponent(component) {
    const ctx = { tag: component, cache: new Map() }
    return createProxy(ctx, classHandler)
}

export const nbsp = '\xA0'
export const hh = new Proxy(_hh, tagHandler)
