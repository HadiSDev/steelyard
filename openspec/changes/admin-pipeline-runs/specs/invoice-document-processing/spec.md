## ADDED Requirements

### Requirement: A document read categorizes the lines it created

The document stage SHALL categorize an invoice's `uncategorized` lines after a
successful extraction replaces them, using the same categorizer and candidates
the sync uses, so a read no longer leaves its lines waiting for the next sync.

- Categorization SHALL run only for an invoice whose extraction succeeded. A
  `failed` extraction keeps its provisional lines as they were.
- A categorization failure SHALL NOT undo the extraction: the invoice stays
  `processed`, and the affected lines follow the usual
  `uncategorized → ai_categorized | ai_failed` lifecycle.
- When the company has no usable spend tree, the lines SHALL stay
  `uncategorized` and the stage's report SHALL say categorization was skipped,
  as the sync does.
- This SHALL hold wherever the stage runs: the CLI, a requested run, or the
  worker's automatic reads.

#### Scenario: Extracted lines leave the read categorized

- **WHEN** the stage reads a pending document for a company with a spend tree
- **THEN** the invoice is `processed` and its extracted lines are
  `ai_categorized` or `ai_failed`, none left `uncategorized`

#### Scenario: A failed extraction categorizes nothing

- **WHEN** an extraction is rejected and the invoice becomes `failed`
- **THEN** no categorization is attempted for that invoice

#### Scenario: No tree, no categorization

- **WHEN** the stage reads a document for a company with no usable spend tree
- **THEN** the invoice is `processed`, its lines stay `uncategorized`, and the
  report says categorization was skipped
