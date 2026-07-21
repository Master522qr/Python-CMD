import sys

name = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "world"
print(f"Hello, {name}!")
