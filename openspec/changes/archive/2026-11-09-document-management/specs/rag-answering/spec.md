## ADDED Requirements

### Requirement: Answer category follows the retrieved documents

The system SHALL report the category of the retrieved documents as the answer category when every retrieved chunk carries a non-empty document category and all of those categories agree; otherwise it SHALL keep the triage category. Escalation and department routing SHALL remain driven by triage alone.

#### Scenario: Unanimous retrieved category wins

- **WHEN** all retrieved chunks come from documents tagged with the same category
- **THEN** the answer reports that category

#### Scenario: Mixed, untagged or empty retrieval keeps the triage category

- **WHEN** retrieved chunks have differing categories, any chunk lacks a category, or nothing is retrieved
- **THEN** the answer reports the triage category
