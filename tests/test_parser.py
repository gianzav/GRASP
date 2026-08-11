import textwrap

import parsy
import pytest
from grasp.model import PatternVariableCollection
from grasp.parser import Pattern, PatternVariable, RuleParser
from pytest import fixture


@fixture
def parser():
    return RuleParser()


def oneline(x):
    return x.replace("\n", "").replace("\t", " ")


def test_parse_exact_rule(parser):
    rule = "@rule-name a :- b. -> a."
    parsed = parser.parse(rule)
    assert oneline(str(parsed)) == "@rule-name a:-b. -> a."


def test_parse_variable_in_pattern(parser):
    rule = "@rule-name ?a :- b. -> a."
    parsed = parser.parse(rule)
    assert oneline(str(parsed)) == "@rule-name ?a:-b. -> a."


def test_parse_variable_collection_in_pattern(parser):
    rule = "@rule-name ?a :- ?body*. -> a."
    parsed = parser.parse(rule)
    assert oneline(str(parsed)) == "@rule-name ?a:-?body*. -> a."


def test_skeleton_variables(parser):
    rule = "@rule-name ?a :- ?b, ?body*. -> $[new] :- $b, $1."
    parsed = parser.parse(rule)
    assert oneline(str(parsed)) == "@rule-name ?a:-?b,?body*. -> $[new] :- $b, $1."


def test_multiple_skeletons(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. -> 
        p :- $a.
        $[new] :- $b, $1.
    """)
    parsed = parser.parse(rule)
    assert (
        oneline(str(parsed))
        == "@rule-name ?a:-?b,?body*. -> p :- $a. $[new] :- $b, $1."
    )


def test_skeleton_variable_vars(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. -> 
        p($body/vars) :- q.
    """)
    parsed = parser.parse(rule)
    assert oneline(str(parsed)) == "@rule-name ?a:-?b,?body*. -> p($body/vars) :- q."


def test_when(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. -> 
        {p} :- $body. when $body
    """)
    parsed = parser.parse(rule)
    assert (
        oneline(str(parsed)) == "@rule-name ?a:-?b,?body*. -> {p} :- $body. when $body"
    )


def test_when_multiple(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. -> 
        {p} :- $body. when $body, $b
    """)
    parsed = parser.parse(rule)
    assert (
        oneline(str(parsed))
        == "@rule-name ?a:-?b,?body*. -> {p} :- $body. when $body, $b"
    )


def test_when_not(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. -> 
        {p} :- $body. when not $body
    """)
    parsed = parser.parse(rule)
    assert (
        oneline(str(parsed))
        == "@rule-name ?a:-?b,?body*. -> {p} :- $body. when not $body"
    )


def test_when_mixed(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. -> 
        {p} :- $body. when $body, not $b
    """)
    parsed = parser.parse(rule)
    assert (
        oneline(str(parsed))
        == "@rule-name ?a:-?b,?body*. -> {p} :- $body. when $body, not $b"
    )


def test_when_variable_expansion(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. ->
        {p} :- $body. when $body/vars
    """)
    parsed = parser.parse(rule)
    assert (
        oneline(str(parsed))
        == "@rule-name ?a:-?b,?body*. -> {p} :- $body. when $body/vars"
    )


def test_when_multiple_variable_expansion(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. ->
        {p} :- $body. when $body/vars, $a/vars
    """)
    parsed = parser.parse(rule)
    assert (
        oneline(str(parsed))
        == "@rule-name ?a:-?b,?body*. -> {p} :- $body. when $body/vars, $a/vars"
    )


def test_parse_multiline_indent_success(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. ->
        {p} :- $body.
    """)
    parsed = parser.parse(rule)
    assert oneline(str(parsed)) == "@rule-name ?a:-?b,?body*. -> {p} :- $body."


def test_parse_multiline_indent_fail(parser):
    rule = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. -> 
        a. -> b.
            b. -> c.
    """)
    with pytest.raises(parsy.ParseError):
        parser.parse(rule)


def test_parse_plus(parser):
    rule = textwrap.dedent("""\
    @lower-bound ?h* :- ?l{?rest*}?u, ?body*. ->
        $h :- $1($body/vars), not $2($body/vars), $body.
        $1($body/vars) :- $l{$rest}, $body.
        $2($body/vars) :- $u+1{$rest}, $body.
    """)
    parser.parse(rule)


def test_parse_plus_pattern(parser):
    pattern = r"s(?x+?y)."
    assert parser.parse_pattern(pattern) == Pattern(
        ["s(", PatternVariable("x"), "+", PatternVariable("y"), ")", "."]
    )


def test_parse_atom_name(parser):
    pattern = r"?name(?args*)."
    assert parser.parse_pattern(pattern) == Pattern(
        [PatternVariable("name"), "(", PatternVariableCollection("args"), ")", "."]
    )
