# FTQP POPL Paper Draft

This directory contains a first POPL-style LaTeX draft for the FTQP / CiPR-FTQC project.

Files:

- `main.tex`: acmart preamble, metadata, abstract, and section inputs.
- `sections/`: all section bodies, including the standalone case-study section and appendix claim-evidence map.
- `sections/writing-brief.md`: shared story, terminology, formula, code, and proof-boundary brief for section-level drafting.
- `references.bib`: bibliography entries used by the draft.
- `Makefile`: convenience build and cleanup commands.

The draft intentionally states the current proof boundary:

- locally checked: core resource/certificate properties in Lean, Python checker invariants, Z3 obligations, GF(2) protocol checks, decoder-table checks, and rectangular geometry checks;
- imported: full physical protocol claims such as flag-circuit single-fault tolerance and architecture-level factory profiles;
- assumed: prototype bridge rules used only for exploratory compiler integration.

Build with a TeX distribution that includes `acmart`:

```bash
make
```

The current machine did not have `latexmk`, `pdflatex`, `xelatex`, `lualatex`, or `tectonic` installed when this draft was created, so only source-level validation was run locally.
