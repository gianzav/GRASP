from asp_rewriting.matcher import RuleMatcher, Match as M, atom
from asp_rewriting.parser import RuleParser


from asp_rewriting.model import PatternVariable as PV
from asp_rewriting.model import PatternVariableCollection as PVC
from asp_rewriting.model import PatternVariableCollection as PVC


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
        M(PVC("h"), "head(X,Y,Z)"),
        ":-",
        "{",
        M(PVC("rest"), "a"),
        "},",
        M(PVC("body"), "p,q,r"),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_cardinality():
    pattern = "?h* :- ?l{?rest*}?u, ?body*."
    rule = "head(X,Y,Z) :- 1{a}2, p, q, r."
    expected = [
        M(PVC("h"), "head(X,Y,Z)"),
        ":-",
        M(PV("l"), "1"),
        "{",
        M(PVC("rest"), "a"),
        "}",
        M(PV("u"), "2"),
        ",",
        M(PVC("body"), "p,q,r"),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_pooling():
    pattern = "?h* :- ?l{?rest[;]*}?u, ?body*."
    rule = "head(X,Y,Z) :- 1{a;b;c;d}2, p, q, r."
    expected = [
        M(PVC("h"), "head(X,Y,Z)"),
        ":-",
        M(PV("l"), "1"),
        "{",
        M(PVC("rest"), "a;b;c;d"),
        "}",
        M(PV("u"), "2"),
        ",",
        M(PVC("body"), "p,q,r"),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_eager():
    pattern = "head :- ?body* p."
    rule = "head :- a,b,c,p."
    expected = ["head", ":-", M(PVC("body"), "a,b,c,"), "p", "."]

    _test_match(pattern, rule, expected)


def test_match_pre_post():
    pattern = "head :- ?bodypre* p, ?bodypost*."
    rule = "head :- a,b,c,p,d,e,f."
    expected = [
        "head",
        ":-",
        M(PVC("bodypre"), "a,b,c,"),
        "p,",
        M(PVC("bodypost"), "d,e,f"),
        ".",
    ]
    _test_match(pattern, rule, expected)


def test_head_choice():
    pattern = "{?h* : ?c*; ?rest[:]*} :- ?body*."
    rule = "{p : q; r : s} :- body."
    expected = [
        "{",
        M(PVC("h"), "p"),
        ":",
        M(PVC("c"), "q"),
        ";",
        M(PVC("rest"), "r:s"),
        "}",
        ":-",
        M(PV("body"), "body"),
        ".",
    ]
    _test_match(pattern, rule, expected)


def test_head_cardinality():
    pattern = "?l{?h1* : ?c1*; ?rest[;:,]*}?u :- ?body*."
    rule = "1{p : q; r : s}2 :- body."
    expected = [
        M(PV("l"), "1"),
        "{",
        M(PVC("h1"), "p"),
        ":",
        M(PVC("c1"), "q"),
        ";",
        M(PVC("rest"), "r:s"),
        "}",
        M(PV("u"), "2"),
        ":-",
        M(PVC("body"), "body"),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_negative_body_cardinality():
    pattern = "?h* :- ?bodypre* not ?l{?rest[:,;]*}?u, ?body*."
    rule = "head :- p, q, not 1{p:r}2, s, t."
    expected = [
        M(PV("h"), "head"),
        ":-",
        M(PVC("bodypre"), "p,q,"),
        "not",
        M(PV("l"), "1"),
        "{",
        M(PVC("rest"), "p:r"),
        "}",
        M(PV("u"), "2"),
        ",",
        M(PV("body"), "s,t"),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_lower_bound():
    pattern = "?h* :- ?l{?rest[:;,]*}?u, ?body*."
    rule = "head :- 1{p : q; r : s}2, t, u."
    expected = [
        M(PVC("h"), "head"),
        ":-",
        M(PV("l"), "1"),
        "{",
        M(PVC("rest"), "p:q;r:s"),
        "}",
        M(PV("u"), "2"),
        ",",
        M(PVC("body"), "t,u"),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_lower_bound_choice():
    pattern = "?h* :- ?bodypre* ?l{?bi* : ?ci*; ?rest[:;,]*}, ?body*."
    rule = "head :- 1{p : q; c : d}, body."
    expected = [
        M(PV("h"), "head"),
        ":-",
        M(PVC("bodypre"), ""),
        M(PV("l"), "1"),
        "{",
        M(PVC("bi"), "p"),
        ":",
        M(PVC("ci"), "q"),
        ";",
        M(PVC("rest"), "c:d"),
        "},",
        M(PVC("body"), "body"),
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_atom_list():
    pattern = "?atoms* d."
    rule = "a,b,c,d."
    expected = [M(PVC("atoms"), "a,b,c,"), "d", "."]

    _test_match(pattern, rule, expected)
