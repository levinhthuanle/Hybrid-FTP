# Hybrid FTP Report

`main.tex` is a professional XeLaTeX report covering all seven required technical-report sections.

## Compile

From this directory, run XeLaTeX twice so the table of contents resolves:

```powershell
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

The generated file is `main.pdf`.

## Required student edits

Search for `\placeholder{` and `[PH]` before submission. In particular, replace:

- title-page institution, instructor, group number, names, IDs, and date;
- all ownership and collaborator entries in Section 4;
- individual self-assessments, peer evaluations, and contribution percentages in Section 5;
- unedited raw GenAI output in Section 6; and
- the screenshot boxes in Section 7 with actual captured evidence.

The technical text, diagrams, verified CLI transcript, and the 67-test result reflect the current implementation. Do not submit the placeholder content as final evidence.
