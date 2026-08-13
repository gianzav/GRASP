import textwrap

from grasp.parser import RuleParser
from grasp.repl import clean_rule_text


def test_clean_rule_text_skips_comment_only_lines():
    input_text = textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. ->
        {p} :- ?body. when ?body
        %
        ?q :- ?body.
    """)
    cleaned = clean_rule_text(input_text)
    assert cleaned == textwrap.dedent("""\
    @rule-name ?a :- ?b, ?body*. ->
        {p} :- ?body. when ?body
        ?q :- ?body.
    """).strip()


def test_clean_rule_text_removes_inline_comments_and_keeps_multiline_rule():
    input_text = textwrap.dedent("""\
    @rule-name a :- b. | % comment before a split
        c :- d. | % comment between subpatterns
        e :- f. ->
        g. % comment after a skeleton item
        h.
    """)
    cleaned = clean_rule_text(input_text)
    assert cleaned == textwrap.dedent("""\
    @rule-name a :- b. | c :- d. | e :- f. ->
        g.
        h.
    """).strip()


def test_parse_rules_accepts_multiline_pattern_alternatives_with_comments():
    input_text = textwrap.dedent("""\
    @rule-name a :- b. | % inline comment
        c :- d. |
        % later comment
        e :- f. ->
        g.
        h.
    """)

    rules = RuleParser().parse_rules(clean_rule_text(input_text))

    assert len(rules) == 1
    assert rules[0].name == "rule-name"
    assert str(rules[0].pattern) == "a:-b. | c:-d. | e:-f."
