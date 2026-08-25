import sys
import traceback

TARGET = "/src/linum/"

def tracer(frame, event, arg):
    if event == "exception":
        exc_type, exc_value, exc_tb = arg

        # Only report our compiler's exception, not Python internals.
        filename = frame.f_code.co_filename
        if TARGET in filename:
            print("\n" + "=" * 78)
            print("REAL EXCEPTION BEFORE CLI CATCH")
            print("=" * 78)
            print(f"File: {filename}")
            print(f"Line: {frame.f_lineno}")
            print(f"Function: {frame.f_code.co_name}")
            print(f"Exception: {exc_type.__name__}: {exc_value}")

            try:
                source = open(filename, encoding="utf-8").read().splitlines()
                lo = max(0, frame.f_lineno - 4)
                hi = min(len(source), frame.f_lineno + 3)

                print("\nSource context:")
                for n in range(lo, hi):
                    marker = " >>> " if n + 1 == frame.f_lineno else "     "
                    print(f"{marker}{n + 1:4}: {source[n]}")
            except Exception:
                pass

            print("\nLocal variable types:")
            for name, value in frame.f_locals.items():
                try:
                    print(
                        f"  {name}: "
                        f"{type(value).__name__} = "
                        f"{value!r}"
                    )
                except Exception:
                    print(f"  {name}: {type(value).__name__}")

            print("=" * 78 + "\n")

    return tracer


sys.settrace(tracer)

import linum.cli as cli

sys.argv = [
    "linum",
    "src/unified_orchestrator.linum",
    "--emit",
    "obj",
    "-o",
    "build/unified_ultimate.o",
]

result = cli.main()
print(f"CLI RESULT: {result}")
