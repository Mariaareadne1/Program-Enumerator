# Program Enumerator

An enumerative program synthesizer for a tiny arithmetic language. Give it
input/output examples; it returns the **smallest** program that fits all of them.

```
$ cat examples/add.txt
1, 2, 3
4, 5, 9
0, 7, 7

$ python synthesizer.py examples/add.txt
+ x y
```

## The language

Programs are written in Polish (prefix) notation:

```
E ::= x | y | 0 | 1 | 2 | + E E | - E E | * E E
```

`x` is the first input, `y` the second. `- * x x y` means `x*x - y`.
A program's **size** is its number of tokens.

## How it works

1. **Size 1:** try the leaves `x, y, 0, 1, 2`.
2. **Size n:** every program is `op L R` where `size(L) + size(R) = n - 1`.
   Build them from the smaller programs already found — nothing is rebuilt from scratch.
3. Go size by size and return the first program whose outputs match every
   example. Because sizes only grow, the answer is minimal.

Each kept program is stored with its outputs on all examples, so
`+ L R` is computed by adding two stored tuples — sub-programs are never re-run.

**Pruning (observational equivalence):** if two programs give identical outputs
on every example (e.g. `+ x y` and `+ y x`), only the first is kept. This makes
the search dramatically smaller without ever missing a smaller solution.
`--no-prune` turns it off for comparison.

## Usage

```
python synthesizer.py examples/add.txt       # one problem per file
python synthesizer.py examples/*.txt         # several problems
cat examples/add.txt | python synthesizer.py # stdin
python synthesizer.py --no-prune FILE        # naive search
python synthesizer.py --max-size 15 FILE     # size limit (default 21)
```

## Tests

```
python -m unittest -v
```

To check against an answer key, add `tests/<name>.txt` (examples) and
`tests/<name>.ans` (expected program) — they're picked up automatically.
