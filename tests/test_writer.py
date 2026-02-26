from asp_rewriting.model import Skeleton, SkeletonVariable as SV
from asp_rewriting.matcher import Bindings
from asp_rewriting.writer import RuleWriter
from asp_rewriting.model import PatternVariable as PV, PatternVariableCollection as PVC
from asp_rewriting.parser import RuleParser


def _test_write(skeleton: str, bindings: Bindings, expected: str):
    skeleton_parsed = RuleParser().parse_skeleton(skeleton)
    writer = RuleWriter()
    result = writer.write(skeleton_parsed, bindings)

    assert result == expected


def test_write_no_vars():
    skeleton = "a :- b."
    bindings: Bindings = Bindings(dict())
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)


def test_one_simple_var():
    skeleton = "$h :- b."
    bindings: Bindings = Bindings({PV("h"): "a"})
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)


def test_two_vars():
    skeleton = "$h :- $body."
    bindings: Bindings = Bindings({PV("h"): "a", PV("body"): "b"})
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)


def test_catchall_body():
    skeleton = "$h :- $body."
    bindings: Bindings = Bindings({PV("h"): "a", PVC("body"): "b,c,d"})
    expected = "a :- b,c,d."

    _test_write(skeleton, bindings, expected)


def test_catchall_head():
    skeleton = "$h :- $body."
    bindings: Bindings = Bindings({PVC("h"): "a;b;c", PVC("body"): "b,c,d"})
    expected = "a;b;c :- b,c,d."

    _test_write(skeleton, bindings, expected)


def test_rewrite_head_1():
    skeleton = "$h :- $c, $body, not $h'."
    bindings: Bindings = Bindings(
        {PV("h"): "head(X)", PV("c"): "cond(X)", PVC("body"): "b, c, d"}
    )
    expected = "head(X) :- cond(X), b, c, d, not head'(X)."

    _test_write(skeleton, bindings, expected)


def test_when_empty_match():
    skeleton = "{$rest} :- $body. when $rest"
    bindings = Bindings({PVC("rest"): "", PVC("body"): "p"})
    expected = ""
    _test_write(skeleton, bindings, expected)


def test_when_nonempty_match():
    skeleton = "{$rest} :- $body. when $rest"
    bindings = Bindings({PVC("rest"): "q", PVC("body"): "p"})
    expected = "{q} :- p."

    _test_write(skeleton, bindings, expected)


def test_fresh_numbered_variable():
    skeleton = "$1 :- $33."
    bindings = Bindings()
    expected = "_0 :- _1."

    _test_write(skeleton, bindings, expected)


def test_fresh_numbered_variable_same_variable_twice():
    skeleton = "$1 :- $1."
    bindings = Bindings()
    expected = "_0 :- _0."

    _test_write(skeleton, bindings, expected)


def test_fresh_named_variable():
    skeleton = "$[a] :- $[a]."
    bindings = Bindings()
    expected = "_0 :- _0."

    _test_write(skeleton, bindings, expected)


def test_fresh_named_variable_extension():
    skeleton = "$[a] :- $[a]'."
    bindings = Bindings()
    expected = "_0 :- _0'."

    _test_write(skeleton, bindings, expected)


def test_vars_expansion():
    skeleton = "$1($body/vars) :- $l{$h1 : $c1; $rest}$u, $body."
    bindings = Bindings(
        {
            PVC("body"): "p(X), q(Y)",
            PV("l"): "1",
            PVC("h1"): "a",
            PVC("c1"): "b",
            PVC("rest"): "",
            PV("u"): "33",
        }
    )
    expected = "_0(X,Y) :- 1{a : b; }33, p(X), q(Y)."
    _test_write(skeleton, bindings, expected)
