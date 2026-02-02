import json
import sys
from html.parser import HTMLParser

current = {'children': []}
stack = [current]

void = ['br', 'img', 'input', 'hr']


class Parser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        elem = {'tag': tag, 'props': attrs, 'children': []}
        stack[-1]['children'].append(elem)
        if tag not in void:
            stack.append(elem)

    def handle_endtag(self, tag):
        stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in void:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if data.strip():
            stack[-1]['children'].append(data)


def print_ast(elem, ident):
    if not elem['props'] and not elem['children']:
        print(ident, elem['tag'], '()', sep='', end='')
        return

    print(ident, elem['tag'], '(', sep='')

    props = dict(elem['props'])
    if props:
        print(ident + '    ', json.dumps(props), ',', sep='')

    for it in elem['children']:
        if isinstance(it, str):
            print(ident + '    ', json.dumps(it.strip()), ',', sep='')
        else:
            print_ast(it, ident + '    ')
            print(',')

    print(ident, ')', sep='', end='')


if __name__ == '__main__':
    parser = Parser()
    parser.feed(sys.stdin.read())

    for it in stack[0]['children']:
        print_ast(it, '')
        print(',')
