# Repository history

In November 2026 this repository was reorganized into a `src/` layout, and
the local development repository of Chromagnon was merged into it **with its
full history**:

| Former repository | Now located at | Tag on its last commit before merging |
|---|---|---|
| Chromagnon (this repository, GitHub) | `src/Chromagnon/` (was `Chromagnon/`) | `import/chromagnon-github` |
| Chromagnon (local development repository) | `src/Chromagnon/` | `import/chromagnon-local` |

Until then, copies of Priithon, PriCommon, common, imgio and ndviewer were
bundled inside the `Chromagnon/` folder. They were removed; Chromagnon now
uses the [Priithon](https://github.com/macronucleus/priithon) package, which
contains imgio, ndviewer and the modules from PriCommon/common that
Chromagnon uses.

## Viewing the history of a file

`git log -- <current path>` only shows commits made after the merge. To see
the older commits, ask for the file at its **old path** starting from the tag:

```bash
# local development history of src/Chromagnon/aligner.py
git log import/chromagnon-local -- aligner.py

# GitHub history before the merge (the package was in Chromagnon/)
git log import/chromagnon-github -- Chromagnon/aligner.py
```

To see the content of a file before the merge:

```bash
git show import/chromagnon-github:Chromagnon/aligner.py
```
