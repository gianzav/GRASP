from asp_rewriting.model import Skeleton, PatternVariable, PatternVariableCollection
from asp_rewriting.matcher import Bindings
from dataclasses import dataclass
from asp_rewriting.model import (
    SkeletonVariable,
    NumberSkeletonVariable,
    NamedSkeletonVariable,
)


def extend_token(token: SkeletonVariable, value: str):
    # the extension is added to a function name before its arguments
    paren_pos = value.find("(")
    if paren_pos > 0:
        atom_name = value[:paren_pos]
        return atom_name + token.extension + value[paren_pos:]
    else:
        return value + token.extension


@dataclass
class RuleWriter:

    def write(self, skeleton: Skeleton, bindings: Bindings) -> str:
        """
        Gives the rewriting based on `skeleton` and the `bindings`.
        """
        result = ""

        # empty result if the 'when' condition of the skeleton is not satisfied
        if skeleton.when:
            value = bindings[skeleton.when]
            if value == "":
                return ""

        for token in skeleton.tokens:

            if isinstance(token, str):
                result += token
            elif isinstance(token, (NumberSkeletonVariable, NamedSkeletonVariable)):
                value = bindings[token]
                result += extend_token(token, value)
            else:
                value = bindings[token]
                var = bindings.get_pattern_variable(token)

                # Write the bound value of the skeleton variable, applying its extension
                if isinstance(var, PatternVariable):
                    # If the pattern variable that is referenced by the skeleton variable is collecting multiple atoms,
                    # the extension is applied to each individual atom in the collection
                    result += extend_token(token, value)
                else:
                    result += value

        return result
