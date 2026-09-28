# Working rules for the HCMUTE RAG project

## Scope and teaching approach

- Follow the approved assignment title exactly: **Tìm hiểu Retrieval Augmented Generation (RAG)**. Do not restore the earlier title wording about researching, designing, and realizing a system.
- Use the teacher's YC1–YC13 numbering from the supplied prompt without renumbering. In particular, YC10 is query handling, answer generation, citations, and refusal; YC11 is RAG evaluation; YC12 is the console application; YC13 is in-depth study.
- Build the console PoC as evidence of understanding, not as a polished UI product. Explain a stage and its alternatives before implementing a material design choice; pause at each agreed checkpoint.
- Keep the main experiment on the HCMUTE corpus. Any external corpus or benchmark requires a source/license proposal and the student's approval first.

## Evidence and reproducibility

- Distinguish measured results, statements from primary sources, and hypotheses. Never invent measurements, citations, source metadata, or completed work.
- Keep corpus snapshot, question split, model/configuration, logs, and evaluation code traceable. Correct labels before interpreting benchmark changes.
- Do not present the milestone-1 `Recall@5` label as standard recall when its implementation counts questions with at least one relevant result in Top-5; describe it as Hit@5 unless the metric is changed and rerun.
- Preserve raw run evidence and identify the exact code/data revision behind each result.

## Data, privacy, and secrets

- Keep source PDFs and extracted full text local and out of Git. The student handbook may contain personal contact information; never send it or derived sensitive text to a cloud model.
- Before using any Gemini task, require a newly rotated key configured locally. Never read, print, log, commit, or paste `.env` or any API key. `.env` is ignored by Git.
- Gemini may only be used for the three approved purposes: evaluator/judge, draft evaluation questions, and image description. Do not use paid API services; stop before any cost-bearing operation unless the student approves an estimate.
- If a source hash differs from the corpus manifest, stop the corpus build and report the mismatch.

## Environment and Git safety

- Use only the dedicated Python 3.11 environment for project commands. Invoke it with its full executable path or `conda run -n rag-hcmute`; print `sys.executable` at the start of each Python run. Do not use the base Python 3.13 environment or `KMP_DUPLICATE_LIB_OK`.
- Install CUDA-enabled PyTorch before `.[dev,dense]`; verify `torch.cuda.is_available()` before dense experiments. Obtain the PyTorch command from official PyTorch documentation and record the exact installed version.
- Work only on `tim-hieu-rag-dot2`, based on `moc1-progress-report`. Keep `main` and PR #2 unchanged. Do not push, merge, open a PR, rewrite history, or delete files/branches unless the student explicitly authorizes that action.
- Do not edit or overwrite the submitted milestone report. Each report revision must be a new file.
- Do not change global Git configuration to work around repository ownership warnings; use a per-command safe-directory setting if needed.
