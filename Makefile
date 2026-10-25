.PHONY: test selfcheck

test:
	python3 -m unittest discover -s tests -v

selfcheck:
	python3 -m apps.pe_inspector.cli --help
	python3 -c 'from apps.pe_inspector.cli import inspect_file; print("import OK")'
