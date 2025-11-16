import { h } from 'preact'
import classNames from 'classnames'

function splitArgs(args) {
    const first = args[0]
    if (first && typeof first == 'object' && !Array.isArray(first) && first.props == undefined) {
        return [first, args.slice(1)]
    }
    return [null, args]
}

function setAttrs(attrs) {
    const pctx = this._wadwise_ctx
    const ctx = { ...pctx, cache: {}, attrs: { ...(pctx.attrs ?? {}), ...attrs } }
    return createProxy(ctx, classHandler)
}

function createProxy(ctx, handler) {
    // console.log('@@ proxy', ctx)
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
    ctx.cache.$ = setAttrs.bind(target)
    return new Proxy(target, handler)
}

function _hh(tag, ...args) {
    const [attrs, children] = splitArgs(args)
    return h(tag, attrs, ...children)
}

_hh._wadwise_ctx = { cache: {} }

const tagHandler = {
    get(target, selector) {
        const [tag, ...clsList] = selector.split('.')
        const cache = target._wadwise_ctx.cache
        if (selector in cache) {
            return cache[selector]
        }
        return (cache[selector] = createProxy({ tag, cache: {}, clsList }, classHandler))
    },
}

const classHandler = {
    get(target, cls) {
        const pctx = target._wadwise_ctx
        const cache = pctx.cache
        if (cls in cache) {
            return cache[cls]
        }
        const ctx = {
            ...pctx,
            cache: {},
            classList: [...(pctx.classList ?? []), ...cls.split('.')],
        }
        return (cache[cls] = createProxy(ctx, classHandler))
    },
}

export const nbsp = '\xA0'
export const hh = new Proxy(_hh, tagHandler)
