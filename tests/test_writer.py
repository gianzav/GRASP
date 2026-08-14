from grasp.model import Skeleton, SkeletonVariable as SV
from grasp.matcher import Bindings, atom
from grasp.writer import RuleWriter
from grasp.model import PatternVariable as PV, PatternVariableCollection as PVC
from grasp.parser import RuleParser
from grasp import model


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
    skeleton = "?h :- b."
    bindings: Bindings = Bindings({PV("h"): _atom("a")})
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)


def test_two_vars():
    skeleton = "?h :- ?body."
    bindings: Bindings = Bindings({PV("h"): _atom("a"), PV("body"): _atom("b")})
    expected = "a :- b."

    _test_write(skeleton, bindings, expected)


def test_catchall_body():
    skeleton = "?h :- ?body."
    bindings: Bindings = Bindings(
        {PV("h"): "a", PVC("body"): [_atom("b"), ",", _atom("c"), ",", _atom("d")]}
    )
    expected = "a :- b,c,d."

    _test_write(skeleton, bindings, expected)


def test_catchall_head():
    skeleton = "?h :- ?body."
    bindings: Bindings = Bindings(
        {
            PVC("h"): [_atom("a"), ";", _atom("b"), ";", _atom("c")],
            PVC("body"): [_atom("b"), ",", _atom("c"), ",", _atom("d")],
        }
    )
    expected = "a;b;c :- b,c,d."

    _test_write(skeleton, bindings, expected)


def test_rewrite_head_1():
    skeleton = "?h :- ?c, ?body, not ?h'."
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
    skeleton = "{?rest} :- ?body. when ?rest"
    bindings = Bindings({PVC("rest"): [], PVC("body"): [_atom("p")]})
    expected = ""
    _test_write(skeleton, bindings, expected)


def test_when_nonempty_match():
    skeleton = "{?rest} :- ?body. when ?rest"
    bindings = Bindings({PVC("rest"): [_atom("q")], PVC("body"): [_atom("p")]})
    expected = "{q} :- p."

    _test_write(skeleton, bindings, expected)


def test_when_multiple():
    skeleton = "{?rest} :- ?body. when ?rest, ?body"
    bindings = Bindings({PVC("rest"): [_atom("q")], PVC("body"): [_atom("p")]})
    expected = "{q} :- p."

    _test_write(skeleton, bindings, expected)


def test_when_not():
    skeleton = "{whoops} :- ?body. when not ?rest"
    bindings = Bindings({PVC("rest"): [], PVC("body"): [_atom("p")]})
    expected = "{whoops} :- p."

    _test_write(skeleton, bindings, expected)


def test_when_mixed():
    skeleton = "{whoops} :- ?body. when ?body, not ?rest"
    bindings = Bindings({PVC("rest"): [], PVC("body"): [_atom("p")]})
    expected = "{whoops} :- p."

    _test_write(skeleton, bindings, expected)


def test_when_variable_expansion():
    skeleton = "{?rest} :- ?body. when ?body/vars"
    bindings = Bindings({PVC("rest"): [_atom("q")], PVC("body"): [_atom("p(X)")]})
    expected = "{q} :- p(X)."

    _test_write(skeleton, bindings, expected)


def test_fresh_numbered_variable():
    skeleton = "?1 :- ?33."
    bindings = Bindings()
    expected = "_new0 :- _new1."

    _test_write(skeleton, bindings, expected)


def test_fresh_numbered_variable_same_variable_twice():
    skeleton = "?1 :- ?1."
    bindings = Bindings()
    expected = "_new0 :- _new0."

    _test_write(skeleton, bindings, expected)


def test_fresh_named_variable():
    skeleton = "?[a] :- ?[a]."
    bindings = Bindings()
    expected = "_a0 :- _a0."

    _test_write(skeleton, bindings, expected)


def test_fresh_named_variable_extension():
    skeleton = "?[a] :- ?[a]'."
    bindings = Bindings()
    expected = "_a0 :- _a0'."

    _test_write(skeleton, bindings, expected)


def test_vars_expansion():
    skeleton = "?1(?body/vars) :- ?l{?h1 : ?c1; ?rest}?u, ?body."
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
    expected = "_new0(X,Y) :- 1{a : b}33, p(X),q(Y)."
    _test_write(skeleton, bindings, expected)


def test_extension_on_collection():
    skeleton = "h :- ?body'."
    bindings = Bindings({PVC("body"): [_atom("p"), ",", _atom("q"), ",", _atom("r")]})
    expected = "h :- p',q',r'."
    _test_write(skeleton, bindings, expected)


def test_extension_on_variable_expansion_collection():
    skeleton = "h :- f(?body/vars')."
    bindings = Bindings(
        {PVC("body"): [_atom("p(X)"), ",", _atom("q(Y)"), ",", _atom("r(Z)")]}
    )
    expected = "h :- f(X',Y',Z')."
    _test_write(skeleton, bindings, expected)


def test_write_binding_error():
    # a variable that doesn't appear in a pattern
    pass


def test_write_pattern_alternatives_no_variable_success():
    # pattern = "{?p : ?c} :- ?body*. | {?p} :- ?body*. | ?p :- ?body*."
    skeleton = ":- ?p, ?c."
    bindings = Bindings({PV("p"): _atom("p"), PV("c"): model.String("")})
    expected = ":- p."
    _test_write(skeleton, bindings, expected)


def test_write_pattern_alternatives_no_var_expansion():
    skeleton = ":- p, ?x/vars, q."
    bindings = Bindings({PV("x"): model.String("")})
    expected = ":- p, q."
    _test_write(skeleton, bindings, expected)


def test_write_empty_pattern_variable_collection_removes_trailing_separators():
    skeleton = ":- p, ?body, q."
    bindings = Bindings({PVC("body"): []})
    expected = ":- p, q."
    _test_write(skeleton, bindings, expected)


def test_write_empty_var_expansion_removes_trailing_separators():
    skeleton = ":- p, ?body/vars, q."
    bindings = Bindings({PVC("body"): []})
    expected = ":- p, q."
    _test_write(skeleton, bindings, expected)


def test_write_empty_multiple_empty_var_expansion():
    skeleton = "?h :- count(?pre/vars, ?body/vars, C), ?body, C >= ?l."
    bindings = Bindings(
        {
            PVC("h"): [_atom("h")],
            PVC("pre"): [],
            PVC("body"): [],
            PV("l"): model.Integer(1),
        }
    )
    expected = "h :- count(C), C >= 1."
    _test_write(skeleton, bindings, expected)


def test_write_empty_multiple_empty_var_expansion_2():
    skeleton = "?[val](?pre/vars, ?bi/vars, ?body/vars) :- ?bi, ?body."
    bindings = Bindings(
        {
            PVC("h"): [_atom("h")],
            PVC("pre"): [_atom("p(X)")],
            PVC("body"): [_atom("q(Y)")],
            PV("l"): model.Integer(1),
            PVC("bi"): [_atom("a")],
        }
    )
    expected = "_val0(X, Y) :- a, q(Y)."
    _test_write(skeleton, bindings, expected)


def test_write_empty_multiple_empty_var_expansion_3():
    skeleton = "?h :- count(?pre/vars, ?body/vars, C), ?pre, ?body, C >= ?l."
    bindings = Bindings(
        {
            PVC("h"): [_atom("h")],
            PVC("pre"): [_atom("p(X)")],
            PVC("body"): [_atom("b(Z)")],
            PV("l"): model.Integer(1),
        }
    )
    expected = "h :- count(X, Z, C), p(X), b(Z), C >= 1."
    _test_write(skeleton, bindings, expected)


def test_write_empty_var_expansion_removes_arithmetic_and_comparison_operators():
    skeleton = ":- p, ?x/vars >= 1."
    bindings = Bindings({PV("x"): model.String("")})
    expected = ":- p >= 1."
    _test_write(skeleton, bindings, expected)


def test_write_pattern_alternatives_no_var_first_in_rule():
    skeleton = ":- ?x, p, q."
    bindings = Bindings({PV("x"): model.String("")})
    expected = ":- p, q."
    _test_write(skeleton, bindings, expected)


def test_write_pattern_alternatives_no_var_middle_in_rule():
    skeleton = ":- ?x, p, q."
    bindings = Bindings({PV("x"): model.String("")})
    expected = ":- p, q."
    _test_write(skeleton, bindings, expected)


def test_write_pattern_alternatives_no_var_in_condition_on_right():
    skeleton = ":- 1{p : ?x}2."
    bindings = Bindings({PV("x"): model.String("")})
    expected = ":- 1{p}2."
    _test_write(skeleton, bindings, expected)


def test_write_with_empty_pattern_variable_collection_match_remove_trailing_separators():
    skeleton = "?h :- ?c, ?body, not ?h'."
    bindings = Bindings(
        {
            PVC("h"): [_atom("a")],
            PVC("c"): model.String(""),
            PVC("rest"): model.String(""),
            PVC("body"): model.String(""),
        }
    )
    expected = "a :- not a'."
    _test_write(skeleton, bindings, expected)


# def test_write_pattern_alternatives_no_var_in_condition_on_left():
#     skeleton = ":- q, 1{?x : p}2."
#     bindings = Bindings({PV("x"): model.String("")})
#     expected = ":- q."
#     _test_write(skeleton, bindings, expected)
