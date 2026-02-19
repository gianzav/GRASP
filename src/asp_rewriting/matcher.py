"""
Author: Gianluca Zavan
Email: gianluca.zavan@aau.at
Affiliation: AAU Klagenfurt


Generation of a custom parser based on a user-defined pattern.
"""

import parsy
from asp_rewriting import model
from dataclasses import dataclass
from typing import Tuple, List, Optional
from asp_rewriting.parser import whitespace, RuleParser, lexeme, comma, semicolon


type VarName = str
type Symbol = str
type Binding = Tuple[VarName, str]

lparen = lexeme(parsy.string("("))
rparen = lexeme(parsy.string(")"))

variable = lexeme(parsy.regex(r"[_A-Z]+[A-Za-z0-9_']*"))
predicate_symbol = lexeme(parsy.regex(r"[a-z]+[A-Za-z0-9'_]*"))
digits = parsy.regex(r"[0-9]+")


@parsy.generate
def atom():
    parens = lambda p: parsy.seq(lparen, p, rparen).combine(
        lambda l, a, r: [l] + a + [r]
    )

    arglist = parsy.seq(
        ((variable | atom) + (comma | semicolon)).many(), (variable | atom)
    ).combine(lambda args, arg: args + [arg])

    name = yield predicate_symbol

    args = None
    args = yield parens(arglist).optional()

    if args:
        return name + "".join(args)
    else:
        return name


@dataclass
class Match:
    variable: model.PatternVariable | model.PatternVariableCollection
    value: Optional[str] = None

    def __eq__(self, other):
        return (
            isinstance(other, Match)
            and self.variable.name == other.variable.name
            and self.value == other.value
        )

    def bind_value(self, value: str):
        return Match(self.variable, value)


@dataclass
class RuleMatcher:
    parser: RuleParser

    def _generate_token_matcher(self, token: model.PatternToken) -> parsy.Parser:
        # match full atoms
        if isinstance(token, model.PatternVariable):
            return lexeme(atom | digits)
        elif isinstance(token, model.PatternVariableCollection):

            over_parser = parsy.alt(*(parsy.string(o) for o in token.over))

            return lexeme(lexeme(atom | digits) + over_parser.optional("")).concat()
        else:  # str
            return lexeme(parsy.string(token))

    def _generate_pattern_matcher(self, pattern: model.Pattern) -> parsy.Parser:
        parser = whitespace.map(lambda x: [])

        for token, next_token in zip(pattern.tokens, list(pattern.tokens)[1:] + [None]):
            # match eagerly all the atoms up to the next token
            if isinstance(token, model.PatternVariableCollection):
                if next_token is not None:
                    this = self._generate_token_matcher(token)
                    next_ = self._generate_token_matcher(next_token)

                    match = Match(token)
                    # parse partially until the next parser is triggered
                    parser += (
                        this.until(next_)
                        .concat()
                        .map(lambda x, m=match: [m.bind_value(x)])
                    )
            elif isinstance(token, str):
                parser += self._generate_token_matcher(token).map(lambda x: [x])
            else:
                match = Match(token)
                parser += self._generate_token_matcher(token).map(
                    lambda x, m=match: [m.bind_value(x)]
                )
        return parser

    def match(self, pattern: str, rule: str) -> List[Match | str]:
        parsed: model.Pattern = self.parser.parse_pattern(pattern)
        matcher = self._generate_pattern_matcher(parsed)
        return matcher.parse(rule)
