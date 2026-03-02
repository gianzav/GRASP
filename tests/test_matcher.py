from asp_rewriting.matcher import RuleMatcher, Match as M, atom
from asp_rewriting.parser import RuleParser


from asp_rewriting.model import PatternVariable as PV
from asp_rewriting.model import PatternVariableCollection as PVC
from asp_rewriting.model import PatternVariableCollection as PVC
from asp_rewriting import model


def _atom(s: str):
    return atom.parse(s)


def _test_match(pattern, rule, expected):
    parser = RuleParser()
    matcher = RuleMatcher(parser)
    matched = matcher.match(pattern, rule)
    assert matched == expected


def test_match_exact():
    pattern = "a :- b."
    rule = "a :- b."
    expected = ["a", ":-", "b", "."]

    _test_match(pattern, rule, expected)


def test_match_atom_no_arguments():
    pattern = "?head :- b."
    rule = "a :- b."
    expected = [M(PV("head"), _atom("a")), ":-", "b", "."]

    _test_match(pattern, rule, expected)


def test_match_atom_with_arguments():
    pattern = "?head :- b."
    rule = "a(p,X,Y) :- b."
    expected = [M(PV("head"), _atom("a(p,X,Y)")), ":-", "b", "."]

    _test_match(pattern, rule, expected)


def test_match_multiple():
    pattern = "a :- ?body*."
    rule = "a :- b,c,d."
    expected = [
        "a",
        ":-",
        M(PVC("body"), [_atom("b"), ",", _atom("c"), ",", _atom("d")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_choice():
    pattern = "?h* :- {?rest*}, ?body*."
    rule = "head(X,Y,Z) :- {a}, p, q, r."
    expected = [
        M(PVC("h"), [_atom("head(X,Y,Z)")]),
        ":-",
        "{",
        M(PVC("rest"), [_atom("a")]),
        "},",
        M(PVC("body"), [_atom("p"), ",", _atom("q"), ",", _atom("r")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_cardinality():
    pattern = "?h* :- ?l{?rest*}?u, ?body*."
    rule = r"head(X,Y,Z) :- 1{a}2, p, q, r."
    expected = [
        M(PVC("h"), [_atom("head(X,Y,Z)")]),
        ":-",
        M(PV("l"), model.Integer(1)),
        "{",
        M(PVC("rest"), [_atom("a")]),
        "}",
        M(PV("u"), model.Integer(2)),
        ",",
        M(PVC("body"), [_atom("p"), ",", _atom("q"), ",", _atom("r")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_pooling():
    pattern = "?h* :- ?l{?rest[;]*}?u, ?body*."
    rule = "head(X,Y,Z) :- 1{a;b;c;d}2, p, q, r."
    expected = [
        M(PVC("h"), [_atom("head(X,Y,Z)")]),
        ":-",
        M(PV("l"), model.Integer(1)),
        "{",
        M(PVC("rest"), [_atom("a"), ";", _atom("b"), ";", _atom("c"), ";", _atom("d")]),
        "}",
        M(PV("u"), model.Integer(2)),
        ",",
        M(PVC("body"), [_atom("p"), ",", _atom("q"), ",", _atom("r")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_eager():
    pattern = "head :- ?body* p."
    rule = "head :- a,b,c,p."
    expected = [
        "head",
        ":-",
        M(PVC("body"), [_atom("a"), ",", _atom("b"), ",", _atom("c"), ","]),
        "p",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_pre_post():
    pattern = "head :- ?bodypre* p, ?bodypost*."
    rule = "head :- a,b,c,p,d,e,f."
    expected = [
        "head",
        ":-",
        M(PVC("bodypre"), [_atom("a"), ",", _atom("b"), ",", _atom("c"), ","]),
        "p,",
        M(PVC("bodypost"), [_atom("d"), ",", _atom("e"), ",", _atom("f")]),
        ".",
    ]
    _test_match(pattern, rule, expected)


def test_head_choice():
    pattern = "{?h* : ?c*; ?rest[:]*} :- ?body*."
    rule = "{p : q; r : s} :- body."
    expected = [
        "{",
        M(PVC("h"), [_atom("p")]),
        ":",
        M(PVC("c"), [_atom("q")]),
        ";",
        M(PVC("rest"), [_atom("r"), ":", _atom("s")]),
        "}",
        ":-",
        M(PVC("body"), [_atom("body")]),
        ".",
    ]
    _test_match(pattern, rule, expected)


def test_head_cardinality():
    pattern = "?l{?h1* : ?c1*; ?rest[;:,]*}?u :- ?body*."
    rule = "1{p : q; r : s}2 :- body."
    expected = [
        M(PV("l"), model.Integer(1)),
        "{",
        M(PVC("h1"), [_atom("p")]),
        ":",
        M(PVC("c1"), [_atom("q")]),
        ";",
        M(PVC("rest"), [_atom("r"), ":", _atom("s")]),
        "}",
        M(PV("u"), model.Integer(2)),
        ":-",
        M(PVC("body"), [_atom("body")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_negative_body_cardinality():
    pattern = "?h* :- ?bodypre* not ?l{?rest[:,;]*}?u, ?body*."
    rule = "head :- p, q, not 1{p:r}2, s, t."
    expected = [
        M(PVC("h"), [_atom("head")]),
        ":-",
        M(PVC("bodypre"), [_atom("p"), ",", _atom("q"), ","]),
        "not",
        M(PV("l"), model.Integer(1)),
        "{",
        M(PVC("rest"), [_atom("p"), ":", _atom("r")]),
        "}",
        M(PV("u"), model.Integer(2)),
        ",",
        M(PVC("body"), [_atom("s"), ",", _atom("t")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_lower_bound():
    pattern = "?h* :- ?l{?rest[:;,]*}?u, ?body*."
    rule = "head :- 1{p : q; r : s}2, t, u."
    expected = [
        M(PVC("h"), [_atom("head")]),
        ":-",
        M(PV("l"), model.Integer(1)),
        "{",
        M(PVC("rest"), [_atom("p"), ":", _atom("q"), ";", _atom("r"), ":", _atom("s")]),
        "}",
        M(PV("u"), model.Integer(2)),
        ",",
        M(PVC("body"), [_atom("t"), ",", _atom("u")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_lower_bound_choice():
    pattern = "?h* :- ?bodypre* ?l{?bi* : ?ci*; ?rest[:;,]*}, ?body*."
    rule = "head :- 1{p : q; c : d}, body."
    expected = [
        M(PVC("h"), [_atom("head")]),
        ":-",
        M(PVC("bodypre"), []),
        M(PV("l"), model.Integer(1)),
        "{",
        M(PVC("bi"), [_atom("p")]),
        ":",
        M(PVC("ci"), [_atom("q")]),
        ";",
        M(PVC("rest"), [_atom("c"), ":", _atom("d")]),
        "},",
        M(PVC("body"), [_atom("body")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_atom_list():
    pattern = "?atoms* d."
    rule = "a,b,c,d."
    expected = [
        M(PVC("atoms"), [_atom("a"), ",", _atom("b"), ",", _atom("c"), ","]),
        "d",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_ignore_spaces():
    pattern = r"{?h* : ?c*} :- ?body*."
    rule = "{a:b} :- p,q."
    expected = [
        "{",
        M(PVC("h"), [_atom("a")]),
        ":",
        M(PVC("c"), [_atom("b")]),
        "}",
        ":-",
        M(PVC("body"), [_atom("p"), ",", _atom("q")]),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_number():
    pattern = r"s(?x)."
    rule = r"s(0)."
    expected = [
        "s(",
        M(PV("x"), model.Integer(0)),
        ")",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_arith_separate():
    pattern = r"s(?x+?y)."
    rule = r"s(X+Y)."
    expected = [
        "s(",
        M(PV("x"), model.Variable("X")),
        "+",
        M(PV("y"), model.Variable("Y")),
        ")",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_arith_together():
    pattern = "s(?x)."
    rule = "s(X+Y)."
    expected = [
        "s(",
        M(
            PV("x"),
            model.Arithmetic("+", [model.Variable("X"), model.Variable("Y")]),
        ),
        ")",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_nested_number():
    pattern = r"s(?x)."
    rule = r"s(s(0))."
    expected = [
        "s(",
        M(PV("x"), _atom("s(0)")),
        ")",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_variables():
    pattern = r"s(?x,?y)."
    rule = r"s(X,Y)."
    expected = [
        "s(",
        M(PV("x"), model.Variable("X")),
        ",",
        M(PV("y"), model.Variable("Y")),
        ")",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_parse_atom_no_args():
    assert _atom("a") == model.Atom("a")


def test_parse_atom_atom_arg():
    assert _atom("a(b)") == model.Atom("a", [model.Atom("b")])


def test_parse_atom_variable_arg():
    assert _atom("a(X)") == model.Atom("a", [model.Variable("X")])


def test_parse_atom_number_arg():
    assert _atom("a(1)") == model.Atom("a", [model.Integer(1)])


def test_parse_atom_mixed_args():
    assert _atom("a(1,b,c(X))") == model.Atom(
        "a", [model.Integer(1), model.Atom("b"), model.Atom("c", [model.Variable("X")])]
    )


def test_parse_atom_variable_args():
    assert _atom("s(X,Y)") == model.Atom(
        "s", [model.Variable("X"), model.Variable("Y")]
    )


def test_parse_atom_arith():
    assert _atom("s(X+Y)") == model.Atom(
        "s", [model.Arithmetic("+", [model.Variable("X"), model.Variable("Y")])]
    )
