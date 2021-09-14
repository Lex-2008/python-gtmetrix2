import re
import os


def list_example(text):
    lines = text.split("\n")

    # skip 1st line
    lineNr = 1

    # pass module docstring unchanged
    while lines[lineNr] != '"""':
        yield lines[lineNr]
        lineNr += 1
        if lineNr >= len(lines):
            return

    # skip end of docstring
    lineNr += 1

    # print out beginning of example code
    yield ""
    yield ".. code-block:: python"
    yield ""

    # skip imports and empty lines
    while (lines[lineNr] == ''
            or lines[lineNr].startswith('import')
            or re.match('from .* import', lines[lineNr])):
        lineNr += 1
        if lineNr >= len(lines):
            return

    # print example until boring part
    while lines[lineNr] != 'if __name__ == "__main__":':
        yield "    " + lines[lineNr]
        lineNr += 1
        if lineNr >= len(lines):
            return
    yield ""


def readfile(filename):
    with open(filename) as f:
        return f.read()


def list_allexamples(directory, outfile):
    all_files = os.listdir(directory)
    py_files = [directory + "/" + filename for filename in all_files if filename.endswith(".py")]
    examples = [readfile(filename) for filename in py_files]
    examples_to_print = sorted([example for example in examples if example.startswith('"""')])

    with open(outfile, "w") as f:
        f.write(readfile(directory + "/examples.rst"))
        for example in examples_to_print:
            for line in list_example(example):
                f.write(line + "\n")


if __name__ == "__main__":
    list_allexamples("../examples", "examples.rst")
