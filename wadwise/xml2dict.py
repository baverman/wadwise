# Simple xml to dict parser
#
# It's usable only for small documents due low performance
# comparing with lxml

from xml.etree import ElementTree as etree

def builder(ptag, attrib, pchild):
    child = []
    data = []

    def start(tag, attrib):
        if tag[0] == '{':
            tag = tag.split('}', 1)[1]

        return builder(tag, attrib, child)

    def fdata(value):
        data.append(value)

    def end():
        cdata = ''.join(data).strip()
        if not child and not attrib:
            pchild.append((ptag, cdata))
        else:
            result = {}
            for name, value in child:
                try:
                    vlist = result[name]
                except KeyError:
                    vlist = result[name] = []

                vlist.append(value)

            for k, v in result.items():
                if len(v) == 1 and type(v[0]) is str:
                    result[k] = v[0]

            if cdata:
                result['#'] = cdata

            if attrib:
                result['$'] = attrib

            pchild.append((ptag, result))

    return start, fdata, end


class DictBuilder:
    def __init__(self):
        self.result = []
        self.stack = []
        self.s, self.d, self.e = builder('root', {}, self.result)

    def start(self, tag, attrib):
        self.stack.append((self.s, self.d, self.e))
        self.s, self.d, self.e = self.s(tag, attrib)

    def data(self, data):
        self.d(data)

    def end(self, tag):
        self.e()
        self.s, self.d, self.e = self.stack.pop()

    def close(self):
        self.e()
        root = self.result[0][1]
        first_elem = root[list(root.keys())[0]]
        if first_elem:
            return first_elem[0]
        else:
            return {}


def parsestring(xml):
    parser = etree.XMLParser(target=DictBuilder())
    parser.feed(xml)
    return parser.close()


if __name__ == '__main__':
    s = '<root><one>boo</one><two>foo</two><one>bar</one></root>'
    print(parsestring(s))
