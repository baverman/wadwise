import ast
from textwrap import dedent

from wadwise.sqlbind_t.tstring import transform_fstrings


def test_simple():
    tree = ast.parse(
        dedent(
            """\
                from wadwise.sqlbind_t.tstring import t
                def boo(name):
                    return t(f'!! SELECT {name}')
            """
        )
    )

    new = transform_fstrings(tree)
    code = compile(new, '<string>', 'exec')
    ctx = {}
    exec(code, ctx, ctx)
    p1, p2 = list(ctx['boo']('zoom'))
    assert p1 == 'SELECT '
    assert p2.value == 'zoom'
