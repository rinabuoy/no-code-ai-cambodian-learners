# Uses latexmk (TeX Live / MacTeX) if present, otherwise tectonic (brew install tectonic).
ENGINE := $(shell command -v latexmk >/dev/null 2>&1 && echo latexmk || echo tectonic)

all:
	@for f in main chapter-1 chapter-2 chapter-3; do if [ "$(ENGINE)" = latexmk ]; then latexmk -xelatex -interaction=nonstopmode $$f.tex; else tectonic -X compile $$f.tex; fi; done

clean:
	rm -f *.aux *.log *.toc *.out *.fls *.fdb_latexmk *.xdv
