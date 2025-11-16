import { cloneElement } from 'preact'
import { signal, computed, batch } from '@preact/signals'

import {
    registerPreactData,
    deleteIdxSignal,
    node2component,
    idify,
    fieldModel,
    preventDefault,
    pushSignal,
    initPreactData,
} from './utils.js'
import { hh as h } from './html.js'

const { div, label, fieldset, legend, input } = h
const button = h.button['pure-button']
const pbutton = button['pure-button-primary']
const vstack = h['v-stack']

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
    pushSignal(
        joints,
        wrapItem({
            id: crypto.randomUUID(),
            parent: '',
            joints: ['', ''],
            assets: [''],
            clear: '',
        }),
    )
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
            div(),
            label(`Party ${pidx + 1}`),
            button({ onClick: preventDefault(() => removeParty(card, pidx)) }, 'Remove party'),
            label('Joint'),
            cloneElement(accountSelector, {
                name: 'joint-other',
                ...fieldModel(card.joints.value[pidx + 1]),
            }),
            label('Asset'),
            cloneElement(accountSelector, {
                name: 'asset-other',
                ...fieldModel(card.assets.value[pidx]),
            }),
        ]
    }

    function jointCard({ card, onDelete }) {
        return div.card(
            { style: { padding: '0.6rem' } },
            vstack(
                h['form-aligned'](
                    label('Main'),
                    cloneElement(accountSelector, { name: 'main', ...fieldModel(card.parent) }),
                    label('Me'),
                    cloneElement(accountSelector, {
                        name: 'me',
                        ...fieldModel(card.joints.value[0]),
                    }),
                    label('Clear'),
                    cloneElement(accountSelector, { name: 'clear', ...fieldModel(card.clear) }),
                    card.assets.value.map((_, pidx) => partyFrag(card, pidx)),
                ),
                div(
                    button({ onClick: preventDefault(() => addParty(card)) }, 'Add Party'),
                    ' ',
                    button({ onClick: preventDefault(onDelete) }, 'Remove Joint'),
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
        fieldset(
            legend('Joint accounts'),
            input({ name: 'data', hidden: true, value: jointsStr }),
            vstack(
                h(JointList, { joints }),
                div(
                    button({ onClick: preventDefault(add) }, 'Add Joint'),
                    ' ',
                    pbutton({ type: 'submit', disabled: hasErrors }, 'Save'),
                ),
            ),
        ),
    ]
}

function FavsForm({ favAccs }) {
    const favs = signal(favAccs.map(signal))

    function FavList() {
        return favs.value.map((it, idx) =>
            div(
                cloneElement(accountSelector, { name: 'acc', ...fieldModel(it) }),
                ' ',
                button({ onClick: preventDefault(() => deleteIdxSignal(favs, idx)) }, '\u2716'),
            ),
        )
    }

    return fieldset(
        legend('Favorites'),
        vstack(
            h(FavList),
            div(
                button({ onClick: preventDefault(() => pushSignal(favs, signal(''))) }, 'Add'),
                ' ',
                pbutton({ type: 'submit' }, 'Save'),
            ),
        ),
    )
}

const accountSelector = node2component(document.querySelector('#accountSelector select'))

registerPreactData(JointForm)
registerPreactData(FavsForm)

export { initPreactData, init }
