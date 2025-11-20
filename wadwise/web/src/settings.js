import { signal, computed, batch } from '@preact/signals'

import {
    registerPreactData,
    deleteIdxSignal,
    idify,
    fieldModel,
    pushSignal,
    initPreactData,
} from './utils.js'
import { hh as h } from './html.js'
import { button, submit, vstack, input, AccountSelector } from './components.js'

const { div, fieldset, legend } = h

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
            div.label(`Party ${pidx + 1}`),
            button({ onClick: () => removeParty(card, pidx) }, 'Remove party'),
            div.label('Joint'),
            AccountSelector({ name: 'joint-other', ...fieldModel(card.joints.value[pidx + 1]) }),
            div.label('Asset'),
            AccountSelector({ name: 'asset-other', ...fieldModel(card.assets.value[pidx]) }),
        ]
    }

    function jointCard({ card, onDelete }) {
        return div.card(
            { style: { padding: '0.6rem' } },
            vstack(
                h['form-aligned'](
                    div.label('Main'),
                    AccountSelector({ name: 'main', ...fieldModel(card.parent) }),
                    div.label('Me'),
                    AccountSelector({ name: 'me', ...fieldModel(card.joints.value[0]) }),
                    div.label('Clear'),
                    AccountSelector({ name: 'clear', ...fieldModel(card.clear) }),
                    card.assets.value.map((_, pidx) => partyFrag(card, pidx)),
                ),
                div(
                    button({ onClick: () => addParty(card) }, 'Add Party'),
                    ' ',
                    button({ onClick: onDelete }, 'Remove Joint'),
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
            input.hidden({ name: 'data', value: jointsStr }),
            vstack(
                h(JointList, { joints }),
                div(
                    button({ onClick: add }, 'Add Joint'),
                    ' ',
                    submit.primary({ disabled: hasErrors }, 'Save'),
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
                AccountSelector({ name: 'acc', ...fieldModel(it) }),
                ' ',
                button({ onClick: () => deleteIdxSignal(favs, idx) }, '\u2716'),
            ),
        )
    }

    return fieldset(
        legend('Favorites'),
        vstack(
            h(FavList),
            div(
                button({ onClick: () => pushSignal(favs, signal('')) }, 'Add'),
                ' ',
                submit.primary('Save'),
            ),
        ),
    )
}

registerPreactData(JointForm)
registerPreactData(FavsForm)

export { initPreactData, init }
