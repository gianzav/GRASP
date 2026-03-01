from asp_rewriting.model import Skeleton, SkeletonVariable as SV
from asp_rewriting.matcher import Bindings, atom
from asp_rewriting.writer import RuleWriter
from asp_rewriting.model import PatternVariable as PV, PatternVariableCollection as PVC
from asp_rewriting.parser import RuleParser


def _atom(s: str):
    return atom.parse(s)


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
    bindings: Bindings = Bindings({PV("h"): _atom("a")})
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)


def test_two_vars():
    skeleton = "$h :- $body."
    bindings: Bindings = Bindings({PV("h"): _atom("a"), PV("body"): _atom("b")})
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)


def test_catchall_body():
    skeleton = "$h :- $body."
    bindings: Bindings = Bindings(
        {PV("h"): "a", PVC("body"): [_atom("b"), ",", _atom("c"), ",", _atom("d")]}
    )
    expected = "a :- b,c,d."

    _test_write(skeleton, bindings, expected)


def test_catchall_head():
    skeleton = "$h :- $body."
    bindings: Bindings = Bindings(
        {
            PVC("h"): [_atom("a"), ";", _atom("b"), ";", _atom("c")],
            PVC("body"): [_atom("b"), ",", _atom("c"), ",", _atom("d")],
        }
    )
    expected = "a;b;c :- b,c,d."

    _test_write(skeleton, bindings, expected)


def test_rewrite_head_1():
    skeleton = "$h :- $c, $body, not $h'."
    bindings: Bindings = Bindings(
        {
            PV("h"): _atom("head(X)"),
            PV("c"): _atom("cond(X)"),
            PVC("body"): [_atom("b"), ",", _atom("c"), ",", _atom("d")],
        }
    )
    expected = "head(X) :- cond(X), b,c,d, not head'(X)."

    _test_write(skeleton, bindings, expected)


def test_when_empty_match():
    skeleton = "{$rest} :- $body. when $rest"
    bindings = Bindings({PVC("rest"): [], PVC("body"): [_atom("p")]})
    expected = ""
    _test_write(skeleton, bindings, expected)


def test_when_nonempty_match():
    skeleton = "{$rest} :- $body. when $rest"
    bindings = Bindings({PVC("rest"): [_atom("q")], PVC("body"): [_atom("p")]})
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
            PVC("body"): [_atom("p(X)"), ",", _atom("q(Y)")],
            PV("l"): "1",
            PVC("h1"): [_atom("a")],
            PVC("c1"): [_atom("b")],
            PVC("rest"): [],
            PV("u"): "33",
        }
    )
    expected = "_0(X,Y) :- 1{a : b; }33, p(X),q(Y)."
    _test_write(skeleton, bindings, expected)


def test_extension_on_collection():
    skeleton = "h :- $body'."
    bindings = Bindings({PVC("body"): [_atom("p"), ",", _atom("q"), ",", _atom("r")]})
    expected = "h :- p',q',r'."
    _test_write(skeleton, bindings, expected)


def test_extension_on_variable_expansion_collection():
    skeleton = "h :- f($body/vars')."
    bindings = Bindings(
        {PVC("body"): [_atom("p(X)"), ",", _atom("q(Y)"), ",", _atom("r(Z)")]}
    )
    expected = "h :- f(X',Y',Z')."
    _test_write(skeleton, bindings, expected)
