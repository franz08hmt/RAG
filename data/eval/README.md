# Evaluation data policy

Question text and gold evidence are assessment data, not filler. A new question or answer is not an approved ground truth until its author has checked the source passage, source version, PDF page, printed page (when available), section, and the smallest evidence span that supports the answer. Never generate “gold” labels solely by asking an LLM.

## Current state

- The approved pilot is in `../question_sets/`: 10 development questions (7 answerable and 3 unanswerable); its gold annotations cover 10 exact evidence spans.
- Five table-focused questions remain a separate `ablation_only` set; they must not be mixed into the development summary or described as a holdout.
- There is no independent holdout and no approved `questions_v2.jsonl`. The requested larger set is therefore **not complete**. No test questions were invented to make a deliverable appear complete.
- Keep source PDFs, full extracted text, OCR text, personal data, and answer excerpts out of this public repository unless a separate licensing/privacy review explicitly permits publication.

## Record format for future questions

Use UTF-8 JSONL with one record per question. The following fields are the minimum; record changes through review rather than silently editing a benchmark:

```json
{
  "question_id": "Q001",
  "question": "Question text reviewed by the student",
  "answerability": "answerable",
  "gold_answer": "Concise answer checked against the source",
  "evidence": [
    {
      "document_id": "DOC_ID",
      "document_sha256": "...",
      "pdf_page": 1,
      "printed_page": null,
      "section_path": "Chapter > Article",
      "quote_sha256": "...",
      "quote": "Exact minimum supporting text, kept only in approved local data"
    }
  ],
  "question_type": ["lexical_gap", "multi_span"],
  "partition": "development",
  "review_status": "student_verified"
}
```

For an unanswerable question, use `"answerability": "unanswerable"`, an empty evidence list, and a short explanation of why the corpus snapshot has no answer. Never use “not found in one retrieval run” as the gold reason for unanswerability. Store the manifest/hash and question split separately; do not tune parameters against a held-out test split.

## Suggested split process

First draft questions from the frozen corpus, then verify exact source evidence manually. Group paraphrases, near-duplicates, and questions derived from the same table/article before splitting, so close variants cannot leak between development and test. Keep a mix of lexical overlap, paraphrase, multi-span, table, scan/OCR, and unanswerable cases. Freeze and hash the test partition before any configuration tuning. If the author cannot audit a source image or scanned page, label that item “pending” and exclude it from metrics.
