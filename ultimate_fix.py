path = 'src/linum/cli.py'

with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Target the exact messy block we discovered and replace it with pristine 12-space indentation
broken_segment = """        except Exception as e:
    import traceback
    traceback.print_exc()
        traceback.print_exc()
            sys.stderr.write(f"Driver execution error during C audit: {str(e)}\\n")
            return 1"""

fixed_segment = """        except Exception as e:
            import traceback
            traceback.print_exc()
            sys.stderr.write(f"Driver execution error during C audit: {str(e)}\\n")
            return 1"""

if broken_segment in text:
    text = text.replace(broken_segment, fixed_segment)
    print("Perfect geometric harmony restored to the C audit block!")
else:
    # Fallback to a broader regex fix just in case spaces vary slightly
    import re
    pattern = r"except Exception as e:\s*import traceback\s*traceback\.print_exc\(\)\s*traceback\.print_exc\(\)"
    text = re.sub(pattern, "except Exception as e:\n            import traceback\n            traceback.print_exc()", text)
    print("Applied regex alignment pass.")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

