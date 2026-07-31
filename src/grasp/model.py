from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Set, Literal
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


@dataclass
class Integer(Term):
    _value: int

    @property
    def name(self) -> str:
        return str(self._value)

    def to_asp(self) -> str:
        return str(self._value)

    def __eq__(self, other) -> bool:
        return isinstance(other, Integer) and self._value == other._value

    def __gt__(self, other) -> bool:
        if isinstance(other, Integer):
            return self._value > other._value
        elif isinstance(other, Atom):
            return True
        raise TypeError(f"Can't compare Integer with value of type {type(other)}")


@dataclass
class String(Term):
    _value: str

    @property
    def name(self) -> str:
        return str(self._value)

    def to_asp(self) -> str:
        return str(self._value)

    def __eq__(self, other) -> bool:
        return isinstance(other, String) and self._value == other._value

    def __gt__(self, other) -> bool:
        if isinstance(other, String):
            return self._value > other._value
        raise TypeError(f"Can't compare String with value of type {type(other)}")


type AtomArg = Term | int | str


@dataclass(init=False)
class Atom(Term):
    _name: str
    args: Sequence[Term] = field(default_factory=list)
    _positive: bool = True
    _separators: List[str] = field(default_factory=list)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    def __init__(
        self,
        name,
        args: Sequence[AtomArg] | Sequence[AtomArg | str] | None = None,
        positive=True,
    ):

        self._name = name
        self._positive = positive
        self._separators: List[Literal[";"] | Literal[","]] = []

        if args and all(isinstance(a, Term) for a in args):
            self.args = [self._convert_arg(a) for a in args]
            self._separators = ["," for _ in range(len(self.args) - 1)]
        elif args:
            self.args = []
            expect_separator = False
            for a in args:
                if expect_separator:
                    if a != "," and a != ";":
                        raise ValueError(
                            f"Expected ';' or ',' after {self.args[-1]}, found {a}"
                        )
                    else:
                        assert isinstance(a, str)
                        self._separators.append(a)
                else:
                    if isinstance(a, (Term | int | str)):
                        self.args.append(self._convert_arg(a))
                    else:
                        raise ValueError(f"Expected term, found {a}")
                expect_separator = not expect_separator
        else:
            self.args = []

    def _convert_arg(self, x: int | str | Term) -> Term:
        if isinstance(x, int):
            return Integer(x)
        elif isinstance(x, str):
            return String(x)
        else:
            return x

    def to_asp(self) -> str:
        _not = "" if self._positive else "not "

        if len(self.args) == 0:
            args = ""
        else:
            args = ""
            for arg, separator in zip(self.args, self._separators + [""]):
                args += f"{arg}{separator}"
            args = "(" + args + ")"
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


@dataclass
class Arithmetic(Atom):
    _name: str
    args: Sequence[Term] = field(default_factory=list)
    _positive: bool = True

    def __post_init__(self):
        if len(self.args) != 2:
            raise ValueError("Arithmetic must have exactly two arguments")

    def to_asp(self) -> str:
        _not = "" if self._positive else "not "
        left, right = self.args

        return f"{_not}{left} {self.name} {right}"


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

    The variable can have an extension, which will be added in its expansion during rewriting.

    E.g. Assume h = p(X)
        - $h' is expanded as p'(X)
        - $h_aux is expanded as p_aux(X)
    """

    name: str
    extension: str = ""

    def __str__(self):
        return f"${self.name}"

    def __hash__(self):
        return hash(self.name)


@dataclass
class NumberSkeletonVariable(SkeletonVariable):
    def __str__(self):
        return f"${self.name}"


@dataclass
class NamedSkeletonVariable(SkeletonVariable):
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
class SkeletonCondition:
    variable: SkeletonVariable
    _positive: bool = True

    def __str__(self):
        not_ = "" if self._positive else "not "
        return f"{not_}{str(self.variable)}"


@dataclass
class Skeleton:
    tokens: Sequence[SkeletonToken]
    when: List[SkeletonCondition] = field(default_factory=list)

    def __str__(self):
        s = "".join(str(x) for x in self.tokens)
        if len(self.when) > 0:
            return s + " when " + ", ".join(str(x) for x in self.when)
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
