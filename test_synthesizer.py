"""
Tests for the synthesizer.  Run with:   python -m unittest -v

Two kinds of checks:
  1. Every example problem in examples/ gets the expected answer.
  2. Pruned and un-pruned search agree on answer SIZE (pruning must never
     make us miss a smaller program).

To check against the course answer key, put the course test files in
tests/ as <name>.txt, and the expected program for each in <name>.ans
(a single line, e.g. "+ x y").  They are picked up automatically.
"""

import glob
import os
import unittest

from synthesizer import evaluate, parse_examples, synthesize

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path) as f:
        return parse_examples(f.read())


class TestEvaluate(unittest.TestCase):
    def test_spec_example(self):
        # "- * x x y" means x*x - y
        self.assertEqual(evaluate("- * x x y", 3, 4), 5)

    def test_leaves(self):
        self.assertEqual(evaluate("x", 7, 9), 7)
        self.assertEqual(evaluate("y", 7, 9), 9)
        self.assertEqual(evaluate("2", 7, 9), 2)


class TestSynthesize(unittest.TestCase):
    EXPECTED = {
        "add.txt": "+ x y",                     # the example from the spec
        "double.txt": "+ x x",
        "square_minus.txt": "- * x x y",
        "sum_of_squares.txt": "+ * x x * y y",
        "three_x_y.txt": "* x + y + y y",
    }

    def test_examples_folder(self):
        for name, expected in self.EXPECTED.items():
            with self.subTest(name=name):
                examples = load(os.path.join(HERE, "examples", name))
                self.assertEqual(synthesize(examples), expected)

    def test_answer_is_correct_and_minimal(self):
        for path in sorted(glob.glob(os.path.join(HERE, "examples", "*.txt"))):
            with self.subTest(path=os.path.basename(path)):
                examples = load(path)
                pruned = synthesize(examples, prune=True)
                naive = synthesize(examples, prune=False, max_size=9)
                # The answer really satisfies every example ...
                for x, y, o in examples:
                    self.assertEqual(evaluate(pruned, x, y), o)
                # ... and is no bigger than what brute force finds.
                self.assertEqual(len(pruned.split()), len(naive.split()))

    def test_course_answer_key(self):
        """Compares against tests/<name>.ans files, if any are present."""
        for path in sorted(glob.glob(os.path.join(HERE, "tests", "*.txt"))):
            answer_path = path[:-4] + ".ans"
            if not os.path.exists(answer_path):
                continue
            with self.subTest(path=os.path.basename(path)):
                with open(answer_path) as f:
                    expected = f.read().strip()
                self.assertEqual(synthesize(load(path)), expected)


if __name__ == "__main__":
    unittest.main()
