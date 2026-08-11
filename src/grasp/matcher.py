"""
Author: Gianluca Zavan
Email: gianluca.zavan@aau.at
Affiliation: AAU Klagenfurt


Generation of a custom parser based on a user-defined pattern.
"""

import parsy
from grasp import model
from dataclasses import dataclass
from typing import List, Optional, Dict, NewType
from grasp.parser import (
    whitespace,
    RuleParser,
    lexeme,
    comma,
    semicolon,
    arith,
    arith_operators,
)
from grasp.model import (
    SkeletonVariable,
    NumberSkeletonVariable,
    NamedSkeletonVariable,
)
import collections
import itertools

VarName = NewType("VarName", str)

lparen = lexeme(parsy.string("("))
rparen = lexeme(parsy.string(")"))

variable = lexeme(parsy.regex(r"[_A-Z]+[A-Za-z0-9_']*")).map(model.Variable)
predicate_symbol = lexeme(parsy.regex(r"[a-z]+[A-Za-z0-9'_]*"))
digits = parsy.regex(r"[0-9]+").map(lambda x: model.Integer(int(x)))
term = parsy.forward_declaration()


def flatten(l: list) -> list:
    return list(itertools.chain.from_iterable(l))


@parsy.generate
def atom():
    separator = comma | semicolon
    withcomma = parsy.seq(term, separator).combine(lambda a, c: [a, c])
    arglist = parsy.seq(
        (withcomma).many().map(flatten),
        term,
    ).combine(lambda args, arg: args + [arg])

    not_ = yield lexeme(parsy.string("not").optional())
    name = yield predicate_symbol

    args = None
    openparen = yield lparen.optional()
    if openparen:
        args = yield arglist.optional()
        yield rparen

    if args:
        return model.Atom(name, args, positive=not_ is None)
    else:
        return model.Atom(name, positive=not_ is None)


type MatchValue = model.Atom | List[model.Atom | str] | model.Integer | model.String


# avoid left-recursion: start binary expressions from a simple term
# (atom, variable or integer) and recurse on the right-hand side only.
simple_term = atom | variable | digits

binary_op = parsy.seq(lexeme(simple_term), lexeme(arith), lexeme(simple_term)).combine(
    lambda left, op, right: model.Arithmetic(op, [left, right])
)

# once the forward declaration is resolved, a term may be a binary expression
# or just a simple term
term.become(binary_op | simple_term)


@dataclass
class Match:
    variable: model.PatternVariable | model.PatternVariableCollection
    value: Optional[MatchValue] = None

    def __eq__(self, other):
        return (
            isinstance(other, Match)
            and self.variable.name == other.variable.name
            and self.value == other.value
        )

    def bind_value(self, value: MatchValue):
        return Match(self.variable, value)


class Bindings:
    def __init__(
        self,
        bindings: (
            Dict[model.PatternVariable | model.PatternVariableCollection, MatchValue]
            | None
        ) = None,
    ):
        self.counter = itertools.count()
        self._bindings = bindings if bindings else dict()
        self._names = {var.name: var for var in self._bindings}
        # bindings for fresh skeleton variables
        self._fresh_bindings: Dict[str, str] = collections.defaultdict(
            lambda: "_new" + str(next(self.counter))
        )

    def get_binding(self, key: VarName | SkeletonVariable) -> MatchValue | str:
        if isinstance(key, str):  # VarName
            _key = self._names[key]
            return self._bindings[_key]
        elif isinstance(key, (NamedSkeletonVariable, NumberSkeletonVariable)):
            return self._fresh_bindings[key.name]
        elif isinstance(key, SkeletonVariable):
            _key = self._names[key.name]
            return self._bindings[_key]
        else:
            raise TypeError(f"Can't access binding for value of type {type(key)}")

    def __getitem__(self, key) -> MatchValue | str:
        return self.get_binding(key)

    def get_pattern_variable(
        self, key: VarName | SkeletonVariable
    ) -> model.PatternVariable | model.PatternVariableCollection:
        if isinstance(key, str):
            return self._names[key]
        elif isinstance(key, SkeletonVariable):
            return self._names[key.name]
        else:
            raise TypeError(f"Can't access binding for value of type {type(key)}")


@dataclass
class RuleMatcher:
    parser: RuleParser

    def _generate_token_matcher(
        self, token: model.PatternToken, next_token: str | None = None
    ) -> parsy.Parser:
        # match full atoms unless the pattern explicitly continues with a
        # left parenthesis; in that case the pattern variable should bind only
        # the name of the atom, not the whole atom with arguments.
        if isinstance(token, model.PatternVariable):
            if next_token == "(":
                return lexeme(parsy.regex(r"[a-z]+[A-Za-z0-9'_]*").map(model.Atom))
            return lexeme(term)
        elif isinstance(token, model.PatternVariableCollection):

            over_parser = parsy.alt(*(parsy.string(o) for o in token.over))

            return lexeme(
                parsy.seq(term, over_parser.optional()).combine(
                    lambda x, y: [x] if y is None else [x, y]
                )
            )
        else:  # str
            return lexeme(parsy.string(token))

    def _generate_pattern_matcher(self, pattern: model.Pattern) -> parsy.Parser:
        parser = whitespace.map(lambda x: [])

        for i, (token, next_token) in enumerate(
            zip(pattern.tokens, list(pattern.tokens)[1:] + [None])
        ):
            # match eagerly all the atoms up to the next token
            if isinstance(token, model.PatternVariableCollection):
                this = self._generate_token_matcher(token)
                match = Match(token)
                parser += this.until(
                    self._generate_pattern_matcher(
                        model.Pattern(pattern.tokens[i + 1 :])
                    )
                ).map(lambda xs, m=match: [m.bind_value(flatten(xs))])
            elif isinstance(token, str):
                parser += self._generate_token_matcher(token).map(lambda x: [x])
            else:  # if token is a PatternVariable
                match = Match(token)
                if isinstance(next_token, str) and next_token in arith_operators:
                    parser += lexeme(simple_term).map(
                        lambda x, m=match: [m.bind_value(x)]
                    )
                else:
                    parser += self._generate_token_matcher(token, next_token).map(
                        lambda x, m=match: [m.bind_value(x)]
                    )
        return parser

    def match(self, pattern: str | model.Pattern, rule: str) -> List[Match | str]:
        if isinstance(pattern, str):
            matcher = self._generate_pattern_matcher(self.parser.parse_pattern(pattern))
        else:
            matcher = self._generate_pattern_matcher(pattern)

        matches = matcher.parse(rule)
        try:
            self._validate_bindings(matches)
        except ValueError as e:
            raise parsy.ParseError(str(e))

        return matches

    def _validate_bindings(
        self, matches: List[Match | str]
    ) -> Dict[model.PatternVariable | model.PatternVariableCollection, MatchValue]:
        bindings: Dict[
            model.PatternVariable | model.PatternVariableCollection, MatchValue
        ] = {}
        variable_matches = [m for m in matches if not isinstance(m, str)]

        for match in variable_matches:
            variable, value = match.variable, match.value

            if value is None:
                raise BindingError(f"None was matched to {variable}")

            if variable in bindings and bindings[variable] != value:
                raise BindingError(
                    f"Variable {str(variable)} can't match on {bindings[variable]} and {value}"
                )

            bindings[variable] = value

        return bindings

    def get_bindings(self, pattern: str, rule: str) -> Bindings:
        matches = self.match(pattern, rule)
        bindings = self._validate_bindings(matches)
        return Bindings(bindings)


class BindingError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
