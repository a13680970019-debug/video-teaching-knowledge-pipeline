# PR Stack Forensics

Repository: a13680970019-debug/video-teaching-knowledge-pipeline

## Read-only local state
- main: 5dfac409c9cc8b7a7856a7df90259ddb09908c82
- PR #2 head: ff471ca51477c4c99f6bc1bf58c6cc5862dbea1d
- PR #4 head: af5fe200cd77adefce3c11c8a51cbd3be11ebf79
- PR #4 merge-base with main: 5dfac409c9cc8b7a7856a7df90259ddb09908c82
- PR #4 commits ahead of main: 7
- PR #4 changed files relative to main: 180
- PR4 stacked on PR2 by local merge-base test: True

## PR #4 commit set relative to main
- af5fe200cd77adefce3c11c8a51cbd3be11ebf79	fix: remediate Gate V2.1 fixed-sample acceptance semantics
- ff471ca51477c4c99f6bc1bf58c6cc5862dbea1d	fix: propagate custom input root into review archive
- f0674f25e42e3b615815af59355fecf093524d57	ci: add synthetic Windows validation
- 5e7738ffb238998ed96d2a68467ea329b1589146	fix: fail closed on real ASR execution
- bfa10e044c4d73b5fb8aba1f9d4c73bd6397fd26	test: add migration regression coverage
- 72886c6f06c4ad384db04a0dac410ed7ec1a8730	feat: import authoritative R2/R2.1 pipeline sources
- cb000712e62da6d8b0594c1f54902a597a54c41c	audit: establish R2/R2.1 execution provenance

## Interpretation
PR #4 is a historical stacked review artifact. Its ancestry includes PR #2. This stage does not rebase, force-push, close, delete, or alter PR #4. A clean branch must be created directly from current main and compared independently.

GitHub compare reference: https://docs.github.com/en/pull-requests/how-tos/commit-changes/comparing-commits

