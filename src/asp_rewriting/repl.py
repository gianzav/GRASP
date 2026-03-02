from parser import RuleParser
from matcher import RuleMatcher
from writer import RuleWriter
import model
import parsy
import logging
import argparse
from dataclasses import dataclass, field
from typing import List, Set


def peek(x):
    y = x.pop()
    x.add(y)
    return y


@dataclass
class Context:
    parser = RuleParser()
    matcher = RuleMatcher(parser)
    writer = RuleWriter()
    rules: List[model.RewritingRule] = field(default_factory=list)
    buffer: Set[str] = field(default_factory=set)


def repl(ctx: Context):

    while True:
        inp = input("::> ").strip()
        match inp:
            case "":
                pass
            case ":rules":
                for rule in ctx.rules:
                    print(str(rule))
            case _:
                evaluate(inp, ctx)


def evaluate(input_, ctx: Context):
    parser = ctx.parser
    matcher = ctx.matcher
    writer = ctx.writer
    rules = ctx.rules
    buffer = ctx.buffer
    done = set()

    try:
        rule = parser.parse(input_)
        rules.append(rule)
    except:
        buffer |= {input_}

        while len(buffer) > 0:
            inp = peek(buffer)
            match = False
            for rule in rules:
                try:
                    bindings = matcher.get_bindings(rule.pattern, inp)
                    match = True
                    buffer.remove(inp)
                    for skeleton in rule.skeletons:
                        rewritten = writer.write(
                            skeleton, bindings, rule_name=rule.name
                        )
                        buffer.add(rewritten)
                        # logging.info(rewritten)
                    break
                except parsy.ParseError as e:
                    logging.debug(
                        f"No match for pattern {str(rule.pattern)} on '{inp}'"
                    )
                    # raise e

            if not match:
                done.add(inp)
                buffer.remove(inp)

        for r in done:
            print(r)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", nargs="?", type=str)
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser


def main():
    argparser = make_parser()
    args = argparser.parse_args()
    ctx = Context()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.filename:
        with open(args.filename, "r") as f:
            # bad pre-processing to eliminate comments
            lines = f.readlines()
            code = ""
            for line in lines:
                before, sep, after = line.partition("%")
                code += before

            rules = code.split("\n\n")
            for rule in rules:
                evaluate(rule, ctx)
        if args.interactive:
            repl(ctx)
    else:
        repl(ctx)


if __name__ == "__main__":
    main()
