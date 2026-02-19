from asp_rewriting.model import Skeleton
from asp_rewriting.matcher import Bindings
from dataclasses import dataclass


@dataclass
class RuleWriter:

    def write(self, skeleton: Skeleton, bindings: Bindings) -> str:
        result = ""
        for token in skeleton.tokens:
            if isinstance(token, str):
                result += token
            else:
                result += bindings[token]

        return result
