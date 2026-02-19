from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Set
import textwrap


class Term:
    @property
    def name(self) -> str:
        raise NotImplementedError

    def to_asp(self) -> str:
        raise NotImplementedError

    def is_positive(self) -> bool:
        return True

    def is_ground(self) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(self.to_asp())

    def __eq__(self, other) -> bool:
        raise NotImplementedError

    def __gt__(self, other) -> bool:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.to_asp()


class ListOfTerms:
    def __init__(self, terms: Sequence[Term]):
        self._terms = terms

    def to_asp(self) -> str:
        return ", ".join(t.to_asp() for t in self._terms)

    def __iter__(self):
        self._iter = iter(self._terms)
        return self._iter

    def __next__(self):
        return next(self._iter)


@dataclass
class Addition(Term):
    left: Term
    right: Term | int

    def to_asp(self) -> str:
        if isinstance(self.right, Term):
            return self.left.to_asp() + " + " + self.right.to_asp()
        else:
            return self.left.to_asp() + " + " + str(self.right)


@dataclass
class LessThan(Term):
    left: Term
    right: Term | int

    def to_asp(self) -> str:
        if isinstance(self.right, Term):
            return self.left.to_asp() + " < " + self.right.to_asp()
        else:
            return self.left.to_asp() + " < " + str(self.right)


@dataclass
class Variable(Term):
    _name: str

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    def to_asp(self) -> str:
        return self.name

    def is_ground(self) -> bool:
        return False

    def __hash__(self) -> int:
        return hash(self.to_asp())

    def __eq__(self, other) -> bool:
        return isinstance(other, Variable) and self.name == other.name

    def __gt__(self, other) -> bool:
        return isinstance(other, Variable) and self.name > other.name

    def __add__(self, other) -> Addition:
        if not isinstance(other, (Term, int)):
            raise TypeError(f"+ undefined for Variable and type '{type(other)}'")
        else:
            return Addition(self, other)

    def __lt__(self, other):
        if not isinstance(other, (Term, int)):
            raise TypeError(f"+ undefined for Variable and type '{type(other)}'")
        else:
            return LessThan(self, other)


@dataclass
class Atom(Term):
    _name: str
    args: Sequence[Term] = field(default_factory=list)
    _positive: bool = True

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    def __post_init__(self):
        def convert(x):
            if isinstance(x, int):
                return Atom(str(x), [])
            elif isinstance(x, str):
                return Atom(f'"{x}"', [])
            else:
                return x

        self.args = [convert(a) for a in self.args]

    def to_asp(self) -> str:
        _not = "" if self._positive else "not "
        args = (
            ""
            if len(self.args) == 0
            else f"({','.join(a.to_asp() for a in self.args)})"
        )
        return f"{_not}{self.name}{args}"

    @property
    def variables(self) -> Set[Variable]:
        vs = set()
        for a in self.args:
            if isinstance(a, Variable):
                vs.add(a)
            elif isinstance(a, Atom):
                vs |= a.variables
            else:
                raise TypeError(f"Can't retrieve variables of Term {a}")
        return vs

    def is_ground(self) -> bool:
        return all(a.is_ground() for a in self.args)

    def __call__(self, *args: Term):
        return Atom(self.name, list(args))

    def __lshift__(self, other: Sequence[Term]):
        return Rule(self, Body(other))

    def __invert__(self):
        return Atom(self.name, self.args, not self._positive)

    def is_positive(self):
        return self._positive

    def __hash__(self) -> int:
        return hash(self.to_asp())

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Atom)
            and self.name == other.name
            and sorted(self.args) == sorted(other.args)
        )

    def __gt__(self, other) -> bool:
        return (
            isinstance(other, Atom)
            and self.name > other.name
            or (self.name == other.name and sorted(self.args) > sorted(other.args))
        )

    def __str__(self):
        return self.to_asp()

    def __add__(self, other) -> Addition:
        if not isinstance(other, Term):
            raise TypeError("+ undefined for Atom and type '{type(other)}'")
        else:
            return Addition(self, other)

    def __lt__(self, other):
        if not isinstance(other, Term):
            raise TypeError("+ undefined for Atom and type '{type(other)}'")
        else:
            return LessThan(self, other)


class Body:
    def __init__(self, terms: Sequence[Term]):
        self.terms = terms

    def __next__(self):
        return next(self._iter)

    def __iter__(self):
        self._iter = iter(self.terms)
        return self._iter

    def is_ground(self) -> bool:
        return all(t.is_ground() for t in self.terms)

    @property
    def positive(self) -> Set[Term]:
        return {t for t in self.terms if t.is_positive()}

    @property
    def negative(self) -> Set[Term]:
        return {t for t in self.terms if not t.is_positive()}

    def __eq__(self, other) -> bool:
        return isinstance(other, Body) and sorted(self.terms) == sorted(other.terms)

    def __gt__(self, other) -> bool:
        return isinstance(other, Body) and sorted(self.terms) > sorted(other.terms)


@dataclass
class Rule:
    head: Term
    body: Body

    def to_asp(self) -> str:
        return f"{self.head.to_asp()} :- {', '.join(b.to_asp() for b in self.body)}."

    def is_safe(self) -> bool:
        raise NotImplementedError

    def is_ground(self) -> bool:
        return self.head.is_ground() and self.body.is_ground()

    def __hash__(self) -> int:
        return hash(self.to_asp())

    @property
    def atoms(self) -> Set[Atom]:
        atoms = set()
        if isinstance(self.head, Atom):
            atoms.add(self.head)
        for t in self.body:
            if isinstance(t, Atom):
                atoms.add(t)
        return atoms

    def __str__(self) -> str:
        return self.to_asp()


@dataclass(init=False)
class Constraint(Rule):

    def __init__(self, body: Body):
        super().__init__(false, body)

    def to_asp(self) -> str:
        return f":- {', '.join(b.to_asp() for b in self.body)}."

    def __hash__(self) -> int:
        return hash(self.to_asp())

    def __eq__(self, other) -> bool:
        return isinstance(other, Constraint) and self.body == other.body

    def __gt__(self, other) -> bool:
        return isinstance(other, Constraint) and sorted(self.body) > sorted(other.body)


@dataclass(init=False)
class Fact(Rule):

    def __init__(self, head: Term):
        super().__init__(head, Body([]))

    def to_asp(self) -> str:
        return f"{self.head.to_asp()}."

    def __hash__(self) -> int:
        return hash(self.to_asp())

    def __eq__(self, other) -> bool:
        return isinstance(other, Fact) and self.body == other.body

    def __gt__(self, other) -> bool:
        return isinstance(other, Fact) and sorted(self.body) > sorted(other.body)


type PredicateSymbol = str


@dataclass
class PatternVariableCollection:
    """
    Variable capturing a collection of symbols/atoms.

    E.g. ?body*

    Optionally, it is possible to define the characters that should be included in a match over many atoms.

    E.g. ?body[;]*

    Means that the variable would match over

    a;b;c

    While ?body* would match by default only over

    a,b,c,d

    If the optional character is defined, the default "," character is not considered and must be explicitly defined.

    E.g. ?body[;]* is NOT equivalent to ?body[,;]*
    """

    name: str
    over: List[str] = field(
        default_factory=lambda: [","]
    )  # subsets of [",", ";", ":", "."]

    def __post_init__(self):
        if self.over is None:
            self.over = [","]

    def __str__(self):
        if self.over and self.over != [","]:
            return f"?{self.name}[{''.join(self.over)}]*"
        else:
            return f"?{self.name}*"

    def __hash__(self):
        return hash(self.name)


@dataclass
class PatternVariable:
    """
    Variable capturing a single symbol/atom.

    E.g. ?h
    """

    name: str

    def __str__(self):
        return f"?{self.name}"

    def __hash__(self):
        return hash(self.name)


@dataclass
class SkeletonVariable:
    """
    Variable used in rewriting skeletons.

    E.g. $h, $1, $[val]

    If the variable name is a number (e.g. $1) or a string in square brackets
    (e.g. $[val]), then it denotes a new symbol which will be generated by the system.
    """

    name: str

    def __str__(self):
        return f"${self.name}"

    def __hash__(self):
        return hash(self.name)


@dataclass
class NumberSkeletonVariable(SkeletonVariable):
    name: str

    def __str__(self):
        return f"${self.name}"


@dataclass
class NamedSkeletonVariable(SkeletonVariable):
    name: str

    def __str__(self):
        return f"$[{self.name}]"


@dataclass
class SkeletonVariableVarExpansion(SkeletonVariable):
    """
    Represents the variables in the atom captured by a skeleton variable

    E.g. $body/vars
    """

    name: str

    def __str__(self):
        return f"${self.name}/vars"


type PatternToken = str | PatternVariable | PatternVariableCollection
type SkeletonToken = str | SkeletonVariable


@dataclass
class Pattern:
    tokens: Sequence[PatternToken]

    def __str__(self):
        return "".join(str(x) for x in self.tokens)


@dataclass
class Skeleton:
    tokens: Sequence[SkeletonToken]
    when: Optional[SkeletonVariable] = None

    def __str__(self):
        s = "".join(str(x) for x in self.tokens)
        if self.when:
            return s + " when " + str(self.when)
        return s


@dataclass
class RewritingRule:
    name: str
    pattern: Pattern
    skeletons: Sequence[Skeleton]

    def __str__(self):
        s = f"@{self.name} {self.pattern} ->\n\t"
        s += "\n\t".join(str(s) for s in self.skeletons)
        return s
