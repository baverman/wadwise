import { cloneElement } from 'preact'
import { signal, computed, batch } from '@preact/signals'

import {
    hh as h,
    registerPreactData,
    deleteIdxSignal,
    node2component,
    idify,
    fieldModel,
    preventDefault,
    pushSignal,
    initPreactData,
} from './utils.js'

function wrapItem(item) {
    return {
        ...item,
        parent: signal(item.parent),
        clear: signal(item.clear),
        joints: signal(item.joints.map(signal)),
        assets: signal(item.assets.map(signal)),
    }
}

const joints = signal([])
const jointsStr = computed(() => JSON.stringify(joints))

const hasErrors = computed(() => {
    return !joints.value.every(
        (it) =>
            it.parent.value &&
            it.clear.value &&
            it.joints.value.every((a) => a.value) &&
            it.assets.value.every((a) => a.value),
    )
})

// import {effect} from '@preact/signals'
// effect(() => console.log(hasErrors.value, joints.value))

function init(data) {
    joints.value = idify(data).map(wrapItem)
}

function add() {
    pushSignal(joints, wrapItem({ id: crypto.randomUUID(), parent: '', joints: ['', ''], assets: [''], clear: '' }))
}

function addParty(item) {
    batch(() => {
        pushSignal(item.joints, signal(''))
        pushSignal(item.assets, signal(''))
    })
}

function removeParty(item, pidx) {
    batch(() => {
        deleteIdxSignal(item.joints, pidx + 1)
        deleteIdxSignal(item.assets, pidx)
    })
}

function JointForm() {
    function partyFrag(card, pidx) {
        return [
            h('div'),
            h('label', `Party ${pidx + 1}`),
            h('button.pure-button', { onClick: preventDefault(() => removeParty(card, pidx)) }, 'Remove party'),
            h('label', 'Joint'),
            cloneElement(accountSelector, { name: 'joint-other', ...fieldModel(card.joints.value[pidx + 1]) }),
            h('label', 'Asset'),
            cloneElement(accountSelector, { name: 'asset-other', ...fieldModel(card.assets.value[pidx]) }),
        ]
    }

    function jointCard({ card, onDelete }) {
        return h(
            'div.card',
            { style: { padding: '0.6rem' } },
            h(
                'v-stack',
                h(
                    'form-aligned',
                    h('label', 'Main'),
                    cloneElement(accountSelector, { name: 'main', ...fieldModel(card.parent) }),
                    h('label', 'Me'),
                    cloneElement(accountSelector, { name: 'me', ...fieldModel(card.joints.value[0]) }),
                    h('label', 'Clear'),
                    cloneElement(accountSelector, { name: 'clear', ...fieldModel(card.clear) }),
                    card.assets.value.map((_, pidx) => partyFrag(card, pidx)),
                ),
                h(
                    'div',
                    h('button.pure-button', { onClick: preventDefault(() => addParty(card)) }, 'Add Party'),
                    ' ',
                    h('button.pure-button', { onClick: preventDefault(onDelete) }, 'Remove Joint'),
                ),
            ),
        )
    }

    function JointList({ joints }) {
        return joints.value.map((card, idx) =>
            h(jointCard, { key: card.id, card, onDelete: () => deleteIdxSignal(joints, idx) }),
        )
    }

    return [
        h(
            'fieldset',
            h('legend', 'Joint accounts'),
            h('input', { name: 'data', hidden: true, value: jointsStr }),
            h(
                'v-stack',
                h(JointList, { joints }),
                h(
                    'div',
                    h('button.pure-button', { onClick: preventDefault(add) }, 'Add Joint'),
                    ' ',
                    h('button.pure-button.pure-button-primary', { type: 'submit', disabled: hasErrors }, 'Save'),
                ),
            ),
        ),
    ]
}

registerPreactData(JointForm)

const accountSelector = node2component(document.querySelector('#accountSelector select'))

export { initPreactData, init }
