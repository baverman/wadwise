from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from .template import Interpolation, Template

UNDEFINED = object()


Part = Union[str, Interpolation]
SQLType = Union['SQL', Template]


class SQL(Template):
    def __or__(self, other: 'SQL') -> 'SQL':
        return OR(self, other)

    def __and__(self, other: 'SQL') -> 'SQL':
        return AND(self, other)

    def __invert__(self) -> 'SQL':
        if self:
            return SQL('NOT ', *self)
        else:
            return EMPTY


class EmptyType(SQL):
    def __iter__(self) -> Iterator[Part]:
        return iter([])

    def __bool__(self) -> bool:
        return False


EMPTY = EmptyType()


def AND(*fragments: SQL) -> SQL:
    return join_fragments(' AND ', fragments, ('(', ')'))


def OR(*fragments: SQL) -> SQL:
    return join_fragments(' OR ', fragments, ('(', ')'))


def join_fragments(sep: str, flist: Sequence[SQL], wrap: Optional[Tuple[str, str]] = None) -> SQL:
    flist = list(filter(None, flist))
    if not flist:
        return EMPTY
    elif len(flist) == 1:
        return flist[0]

    result: list[Part] = []
    if wrap:
        result.append(wrap[0])
    for it in flist:
        result.extend(it)
        result.append(sep)
    result.pop()
    if wrap:
        result.append(wrap[1])
    return SQL(*result)


def prefix_join(prefix: str, sep: str, flist: Sequence[SQL], wrap: Optional[Tuple[str, str]] = None) -> SQL:
    e = join_fragments(sep, flist, wrap)
    return SQL(prefix, *e) if e else EMPTY


def WHERE(*cond: SQL, **kwargs: Any) -> SQL:
    flist = list(cond) + [
        SQL(f'{field} IS NULL') if value is None else SQL(f'{field} = ', Interpolation(value))
        for field, value in kwargs.items()
        if value is not UNDEFINED
    ]
    return prefix_join('WHERE ', ' AND ', flist)


def VALUES(data: Optional[List[Dict[str, Any]]] = None, **kwargs: Any) -> SQL:
    if data is None:
        data = [kwargs]

    names = list(data[0].keys())
    result: List[Part] = [f"({', '.join(names)}) VALUES "]
    for it in data:
        result.append('(')
        for f in names:
            result.extend((Interpolation(it[f]), ', '))
        result.pop()
        result.append(')')
        result.append(', ')

    result.pop()
    return SQL(*result)


def assign(**kwargs: Any) -> SQL:
    flist = [SQL(f'{field} = ', Interpolation(value)) for field, value in kwargs.items() if value is not UNDEFINED]
    return join_fragments(', ', flist)


def SET(**kwargs: Any) -> SQL:
    return SQL('SET ', *assign(**kwargs))


def text(expr: str) -> SQL:
    return SQL(expr)


class NotNone:
    def __truediv__(self, other: Any) -> Any:
        if other is None:
            return UNDEFINED
        return other


not_none = NotNone()


def _in_range(field: str, lop: str, left: Any, rop: str, right: Any) -> SQL:
    return AND(
        SQL(f'{field} {lop} ', Interpolation(left)) if left is not UNDEFINED else EMPTY,
        SQL(f'{field} {rop} ', Interpolation(right)) if right is not UNDEFINED else EMPTY,
    )


def in_range(field: str, left: Any, right: Any) -> SQL:
    return _in_range(field, '>=', left, '<', right)


def in_crange(field: str, left: Any, right: Any) -> SQL:
    return _in_range(field, '>=', left, '<=', right)


class ListQueryParams:
    mark: str

    def render(self, sql: SQLType) -> Tuple[str, List[Any]]:
        params: List[Any] = []
        return ''.join(self.iter(sql, params)), params

    def iter(self, sql: SQLType, params: List[Any]) -> Iterator[str]:
        mark = self.mark
        for it in sql:
            if type(it) is str:
                yield it
            else:
                yield mark
                params.append(it.value)  # type: ignore[union-attr]


class QMarkQueryParams(ListQueryParams):
    mark = '?'
