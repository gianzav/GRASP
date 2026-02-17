"""
Author: Gianluca Zavan
Email: gianluca.zavan@aau.at
Affiliation: AAU Klagenfurt

Parser for the input language of the term rewriting system.
The parser is able to handle rewriting rules such as:

```
@head-cardinality ?l{?h1 : ?c1*; ?rest*}?u :- ?body*. ->
    % First transform the choice rule
    $h1  :- $c1, $body, not $h1'.
    $h1' :- $c, $body, not $h1.
    {$rest} :- $body. when $rest
    % Add the other rule
    $1($body/vars) :- $l{$h1 : $c1; $rest}$u, $body.
    :- not $1($body/vars), $body.
```

Where
  - ?l, ?h1, ?c1*, ?rest* etc. are pattern variables that can be used for rewriting
  - $h1 etc. are references to such variables in the rewriting
  - Lines starting with % are treated as comments
  - `when` is a keyword that allows to perform a conditional rewriting
"""

from parsy import forward_declaration, regex, seq, string, generate, fail
from dataclasses import dataclass
from asp_rewriting.model import *

# Utilities
whitespace = regex(r"\s*")
lexeme = lambda p: p << whitespace

# Punctuation
lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
lbrack = lexeme(string("["))
rbrack = lexeme(string("]"))
colon = lexeme(string(":"))
comma = lexeme(string(","))
at = string("@")
semicolon = lexeme(string(";"))
dot = lexeme(string("."))
arrow = lexeme(string("->"))
impl = lexeme(string(":-"))
newline = lexeme(string("\n"))

# Primitives

number = lexeme(regex(r"-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?")).map(float)
string_part = regex(r'[^"\\]+')

rule_name = lexeme(at >> regex(r"[A-Za-z\-]+"))

pattern_rule_head = lexeme(regex(r"[A-Za-z0-9\-\{\}]"))
pattern_rule_head = lexeme(regex(r"[A-Za-z0-9\-\{\}]"))
pattern_rule_body = lexeme(regex(r"[A-Za-z0-9\-\{\}]"))

pattern_rule = (
    pattern_rule_head.optional() + lexeme(string(":-")) + pattern_rule_body + dot
)


fact = pattern_rule_head + dot
constraint = impl + pattern_rule_body + dot
rule = pattern_rule_head + impl + pattern_rule_body + dot

pattern_rule = constraint | fact | rule
skeleton_rule = constraint | fact | rule


@generate
def rewriting_rule():
    name = yield rule_name
    pattern = yield pattern_rule
    yield arrow
    skeletons = yield skeleton_rule.at_least(1)
    return RewritingRule(name, pattern, skeletons)


@dataclass
class RuleParser:

    def parse(self, rule: str) -> RewritingRule:
        return rewriting_rule.parse(rule)
