"""
Enumerative program synthesizer for a tiny arithmetic DSL.

PROBLEM
-------
We are given input/output examples, one per line:

    i_1, i_2, o_1

and we must find a program P such that P(i_1, i_2) == o_1 for EVERY example.

DSL (written in Polish / prefix notation):

    E ::= x | y | 0 | 1 | 2 | + E E | - E E | * E E

    x  -> the first input  (i_1)
    y  -> the second input (i_2)
    "- * x x y"  means  (x * x) - y

SIZE of a program = number of tokens.  "+ x y" has size 3.

STRATEGY (bottom-up enumeration)
--------------------------------
1. Size-1 programs are just the leaves: x, y, 0, 1, 2.
2. A program of size n is an operator (1 token) applied to a left
   sub-program of size L and a right sub-program of size R, with
   1 + L + R == n.  So we build size n entirely out of programs we
   already built at smaller sizes.
3. We go size 1, 2, 3, ... and return the FIRST program that matches
   every example.  Because sizes increase, that program is guaranteed
   to be one of the smallest possible.

Note: every operator takes exactly two arguments, so every program has
an odd size (1, 3, 5, ...).  Even sizes are simply empty.

SPEED-UP (observational equivalence pruning, on by default)
----------------------------------------------------------
Instead of just remembering a program, we also remember its OUTPUTS on
all the examples (its "signature").  If two programs produce identical
outputs on every example, they are interchangeable for our purposes --
any bigger program built from one behaves exactly like the same program
built from the other.  So we keep only the FIRST (smallest) program for
each signature and throw later duplicates away.

Example: "+ x y" and "+ y x" always give the same outputs, so only
"+ x y" is kept.  This shrinks the search enormously while still
guaranteeing a minimum-size answer.  Run with --no-prune to see the
naive, un-pruned search.

USAGE
-----
    python synthesizer.py examples.txt          # one problem per file
    python synthesizer.py tests/*.txt           # many problems
    cat examples.txt | python synthesizer.py    # read from stdin
    python synthesizer.py --no-prune ex.txt     # disable pruning
    python synthesizer.py --max-size 15 ex.txt  # change the size limit
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# The DSL
# ---------------------------------------------------------------------------

# Leaf tokens, in the order the grammar lists them.  The order matters: when
# several programs of the same size all work, the one enumerated first wins.
LEAVES = ["x", "y", "0", "1", "2"]

# Binary operators, again in grammar order, mapped to the Python function
# that computes them.
OPERATORS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
}

# A type alias for readability: an Example is (i_1, i_2, o_1).
Example = Tuple[int, int, int]


# ---------------------------------------------------------------------------
# Parsing the input file
# ---------------------------------------------------------------------------

def parse_examples(text: str) -> List[Example]:
    """Turn lines like '1, 2, 3' into a list of (1, 2, 3) tuples.

    Blank lines and lines starting with '#' are ignored, so test files
    can contain comments.
    """
    examples = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            raise ValueError(
                f"line {line_number}: expected 'i_1, i_2, o_1', got {line!r}"
            )
        i1, i2, o1 = (int(p) for p in parts)
        examples.append((i1, i2, o1))
    if not examples:
        raise ValueError("no examples found")
    return examples


# ---------------------------------------------------------------------------
# Evaluating a program (used for checking answers and in the tests)
# ---------------------------------------------------------------------------

def evaluate(program: str, x: int, y: int) -> int:
    """Run a Polish-notation program string on inputs x and y.

    Example: evaluate("- * x x y", 3, 4)  ->  3*3 - 4  ->  5

    We read tokens left to right.  A leaf returns its value; an operator
    first evaluates its left argument, then its right argument, then
    combines them.  This recursive reading is exactly what prefix
    notation means, and it's why no parentheses are needed.
    """
    tokens = program.split()
    position = 0  # index of the next token to read

    def parse() -> int:
        nonlocal position
        token = tokens[position]
        position += 1
        if token == "x":
            return x
        if token == "y":
            return y
        if token in OPERATORS:
            left = parse()   # consumes the left sub-program's tokens
            right = parse()  # then the right sub-program's tokens
            return OPERATORS[token](left, right)
        return int(token)  # a constant: 0, 1 or 2

    result = parse()
    if position != len(tokens):
        raise ValueError(f"extra tokens in program: {program!r}")
    return result


# ---------------------------------------------------------------------------
# The synthesizer
# ---------------------------------------------------------------------------

def synthesize(
    examples: List[Example],
    max_size: int = 21,
    prune: bool = True,
) -> Optional[str]:
    """Return the first (smallest) program consistent with all examples.

    Returns None if nothing up to `max_size` tokens works.
    """
    xs = [ex[0] for ex in examples]            # all the i_1 values
    ys = [ex[1] for ex in examples]            # all the i_2 values
    target = tuple(ex[2] for ex in examples)   # the outputs we want

    # programs_by_size[n] is a list of (program_text, outputs) pairs for
    # every program of size n that we are keeping.  `outputs` is a tuple
    # holding the program's result on each example, in order.  Storing the
    # outputs means we never re-run a sub-program: building "+ A B" just
    # adds A's outputs and B's outputs element by element.
    programs_by_size: Dict[int, List[Tuple[str, tuple]]] = {}

    # With pruning on, `seen` records every output-tuple we have already
    # produced, so a later program with the same behaviour is skipped.
    seen = set()

    def consider(program: str, outputs: tuple, bucket: list) -> bool:
        """Keep a newly built program; return True if it solves the task."""
        if prune:
            if outputs in seen:
                return False          # duplicate behaviour -> discard
            seen.add(outputs)
        bucket.append((program, outputs))
        return outputs == target

    # --- Size 1: the leaves --------------------------------------------
    leaf_values = {
        "x": tuple(xs),
        "y": tuple(ys),
        "0": tuple(0 for _ in examples),
        "1": tuple(1 for _ in examples),
        "2": tuple(2 for _ in examples),
    }
    size_one = []
    programs_by_size[1] = size_one
    for leaf in LEAVES:
        if consider(leaf, leaf_values[leaf], size_one):
            return leaf

    # --- Sizes 2, 3, 4, ...: combine smaller programs ---------------------
    for size in range(2, max_size + 1):
        bucket: List[Tuple[str, tuple]] = []
        programs_by_size[size] = bucket

        # One token goes to the operator, so the two children share
        # size - 1 tokens.  Try every way of splitting them: left gets
        # 1 token, 2 tokens, ... up to size - 2 (the right needs >= 1).
        for op_token, op_fn in OPERATORS.items():
            for left_size in range(1, size - 1):
                right_size = size - 1 - left_size
                left_programs = programs_by_size[left_size]
                right_programs = programs_by_size[right_size]
                if not left_programs or not right_programs:
                    continue  # e.g. even sizes have no programs

                for left_text, left_out in left_programs:
                    for right_text, right_out in right_programs:
                        # Compute the new program's outputs from its
                        # children's outputs, one example at a time.
                        outputs = tuple(
                            op_fn(a, b) for a, b in zip(left_out, right_out)
                        )
                        program = f"{op_token} {left_text} {right_text}"
                        if consider(program, outputs, bucket):
                            return program

    return None  # no program found within the size limit


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enumerative synthesizer for + - * arithmetic programs."
    )
    parser.add_argument(
        "files", nargs="*",
        help="example files (one problem per file); reads stdin if omitted",
    )
    parser.add_argument(
        "--max-size", type=int, default=21,
        help="largest program size (in tokens) to try (default: 21)",
    )
    parser.add_argument(
        "--no-prune", action="store_true",
        help="disable observational-equivalence pruning (much slower)",
    )
    args = parser.parse_args()

    # Gather (label, text) for each problem to solve.
    if args.files:
        problems = []
        for path in args.files:
            with open(path) as f:
                problems.append((path, f.read()))
    else:
        problems = [(None, sys.stdin.read())]

    for label, text in problems:
        examples = parse_examples(text)
        result = synthesize(
            examples, max_size=args.max_size, prune=not args.no_prune
        )
        answer = result if result is not None else "NO SOLUTION FOUND"
        # With several files, prefix each answer with its file name.
        print(f"{label}: {answer}" if len(problems) > 1 else answer)


if __name__ == "__main__":
    main()
