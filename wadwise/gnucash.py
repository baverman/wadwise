# type: ignore
from base64 import urlsafe_b64encode
from binascii import unhexlify
from datetime import datetime
from xml.etree import ElementTree as ET

from covador import item, make_schema, opt

from wadwise import model as m


class XmlGetter:
    def __init__(self, ns=None):
        self.ns = ns

    def get(self, elem, item):
        if item.multi:
            return elem.findall(item.src, self.ns)
        else:
            return elem.find(item.src, self.ns)


def xml_text(elem):
    return elem.text


def gnc_val(value):
    p1, p2 = value.split('/')
    return int(p1) / int(p2)


def b64id(value):
    return urlsafe_b64encode(unhexlify(value)).decode().rstrip('=')


def date_t(value):
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S %z')


gnucash_ns = {
    'gnc': 'http://www.gnucash.org/XML/gnc',
    'act': 'http://www.gnucash.org/XML/act',
    'trn': 'http://www.gnucash.org/XML/trn',
    'cmdty': 'http://www.gnucash.org/XML/cmdty',
    'split': 'http://www.gnucash.org/XML/split',
    'ts': 'http://www.gnucash.org/XML/ts',
    'slot': 'http://www.gnucash.org/XML/slot',
}


def slot_dict(value):
    return {it['key']: it['value'] for it in value}


gnc_schema = make_schema(XmlGetter(gnucash_ns))

slot_t = gnc_schema(key=item(xml_text, src='slot:key'), value=item(xml_text, src='slot:value'))

account_t = gnc_schema(
    aid=item(xml_text, src='act:id') | b64id,
    name=item(xml_text, src='act:name'),
    type=item(xml_text, src='act:type'),
    cur=item(xml_text, src='act:commodity/cmdty:id'),
    parent=opt(xml_text, src='act:parent') | b64id,
    slots=item(slot_t, multi=True, src='act:slots/slot') | slot_dict,
)

op_t = gnc_schema(
    # value=item(xml_text, src='split:value') | gnc_val,
    amount=item(xml_text, src='split:quantity') | gnc_val,
    account=item(xml_text, src='split:account') | b64id,
)

transaction_t = gnc_schema(
    tid=item(xml_text, src='trn:id') | b64id,
    cur=item(xml_text, src='trn:currency/cmdty:id'),
    date=item(xml_text, src='trn:date-posted/ts:date') | date_t,
    desc=item(xml_text, src='trn:description'),
    ops=item(op_t, multi=True, src='trn:splits/trn:split'),
)

gnc_data = gnc_schema(
    accounts=item(account_t, multi=True, src='gnc:book/gnc:account'),
    transactions=item(transaction_t, multi=True, src='gnc:book/gnc:transaction'),
)


def import_data(fname):
    root = ET.parse(fname)
    data = gnc_data(root)
    m.drop_tables()
    m.create_tables()

    acc_types = {
        'INCOME': m.AccType.INCOME,
        'ASSET': m.AccType.ASSET,
        'BANK': m.AccType.ASSET,
        'CREDIT': m.AccType.ASSET,
        'EXPENSE': m.AccType.EXPENSE,
        'EQUITY': m.AccType.EQUITY,
        'LIABILITY': m.AccType.LIABILITY,
    }

    accs = {}
    parents = {}
    for it in data['accounts']:
        accs[it['aid']] = it
        parents.setdefault(it['parent'], []).append(it)

    def make_children_acc(parent):
        for it in parents.get(parent, []):
            if it['name'] == it['cur']:
                it['aid'] = parent
                continue

            if it['name'].endswith(' ' + it['cur']):
                nm = it['name'][: -len(' ' + it['cur'])]
                acc = next((fit for fit in parents[parent] if fit['name'] == nm), None)
                if acc:
                    it['aid'] = acc['aid']
                    continue

            m.create_account(
                parent,
                it['name'],
                acc_types[it['type']],
                aid=it['aid'],
                is_placeholder=it['slots']['placeholder'] == 'true',
            )
            make_children_acc(it['aid'])

    root = parents[None][0]['aid']
    parents[None] = parents.pop(root)
    make_children_acc(None)

    for trn in data['transactions']:
        ops = [m.op(accs[op['account']]['aid'], op['amount'], accs[op['account']]['cur']) for op in trn['ops']]
        m.create_transaction(ops, int(trn['date'].timestamp()), trn['desc'])
