from asp_rewriting.model import Skeleton
from asp_rewriting.matcher import Bindings
from asp_rewriting.writer import RuleWriter


def _test_write(skeleton: Skeleton, bindings: Bindings, expected: str):
    writer = RuleWriter()
    result = writer.write(skeleton, bindings)

    assert result == expected


def test_write_no_vars():
    skeleton = Skeleton(["a :- b."])
    bindings: Bindings = dict()
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)
