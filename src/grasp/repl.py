from grasp.parser import RuleParser
from grasp.matcher import RuleMatcher, BindingError
from grasp.writer import RuleWriter
import grasp.model as model
import parsy
import logging
import argparse
from dataclasses import dataclass, field
from typing import List, Set
import sys


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
                if ctx.rules:
                    for rule in ctx.rules:
                        print(str(rule))
                else:
                    print("No rule defined")
            case ":exit":
                sys.exit(0)
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
                except BindingError as e:
                    logging.debug(e.msg)

            if not match:
                done.add(inp)
                buffer.remove(inp)

        for r in done:
            print(r)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*", type=str)
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser


def main():
    argparser = make_parser()
    args = argparser.parse_args()
    ctx = Context()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.filenames:
        for file in args.filenames:
            with open(file, "r") as f:
                text = f.read()

            # remove comments and preserve newlines so rules can still be
            # separated by blank lines or indentation.
            cleaned_lines = []
            for line in text.splitlines():
                before, sep, after = line.partition("%")
                cleaned_lines.append(before.rstrip())
            cleaned_text = "\n".join(cleaned_lines).strip()

            if not cleaned_text:
                continue

            try:
                rules = ctx.parser.parse_rules(cleaned_text)
            except parsy.ParseError as e:
                raise ValueError(f"Failed to parse rules from file {file}: {e}")

            for rule in rules:
                ctx.rules.append(rule)

        if args.interactive:
            repl(ctx)
    else:
        repl(ctx)


if __name__ == "__main__":
    main()
