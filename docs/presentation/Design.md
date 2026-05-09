# Rise Hire Presentation Design System (Execution Rules)

This file defines the non-negotiable design rules for all four PDF deliverables.

Status: **planning only**. No redesign/build starts until you approve this.

---

## 1. Scope and constraints

1. Theme: **light mode first** (no dark canvases except tiny accent blocks if needed).
2. Readability over decoration.
3. First three PDFs (PRD, API, Sprints): **A4 portrait**.
4. Architecture PDF: **landscape system map format** (16:10 recommended).
5. Each PDF is **multi-page and detailed**, not one-page.

---

## 2. External research findings (what this system is based on)

### 2.1 Award-style direction
1. Awwwards minimal guidance highlights: minimalism relies on **balance, alignment, contrast**.
2. Behance presentation/branding galleries show strong use of:
   - clear section rhythm,
   - bold headings + restrained body text,
   - high whitespace discipline,
   - limited color systems.

### 2.2 Readability and hierarchy
1. Interaction Design Foundation: visual hierarchy should use size, contrast, alignment, proximity, whitespace, repetition, clear focal points.
2. Smashing (line length/readability): target practical body line length around **45-85 characters** per line.
3. WCAG 2.1 contrast minimum:
   - normal text >= 4.5:1,
   - large text >= 3:1.

### 2.3 Figma usage references
1. Figma Auto Layout docs:
   - use auto layout for dynamic resizing and consistent spacing,
   - use Hug/Fill/Fixed intentionally,
   - nested structure for complex pages.
2. Figma Constraints docs:
   - constraints define resize behavior for non-auto-layout layers,
   - avoid random scaling behavior by explicitly setting horizontal/vertical constraints.

### 2.4 Figma bridge implementation quirks (from audited local bridge)
1. Use `parentRef` and `nodeRef` (not `parentId` / `nodeId`).
2. Text content uses `characters` (not `text`).
3. Fill format: `fills: [{"type":"SOLID","color":"#XXXXXX"}]`.
4. Use small operation batches (about 6 ops) to avoid timeout risk.
5. Prevent overflow by mandatory text sizing sequence where needed:
   - create text,
   - set text style / autoresize behavior,
   - resize to constrained width.

---

## 3. Visual language (light mode)

## 3.1 Color tokens
| Token | Hex | Usage |
|---|---|---|
| bg-page | `#F8FAFC` | page background |
| bg-panel | `#FFFFFF` | cards / content surfaces |
| stroke-soft | `#E2E8F0` | separators, table lines |
| text-primary | `#0F172A` | titles, core text |
| text-secondary | `#334155` | secondary paragraphs |
| text-muted | `#64748B` | captions, notes |
| brand-blue | `#2563EB` | primary brand accent |
| brand-cyan | `#0891B2` | secondary accent |
| success | `#16A34A` | positive/status success |
| warning | `#D97706` | warnings/highlights |
| danger | `#DC2626` | critical/error emphasis |

## 3.2 Typography scale (Inter)
| Role | Size | Weight | Line-height |
|---|---:|---|---:|
| H1 | 40 | Bold | 48 |
| H2 | 30 | Bold | 38 |
| H3 | 24 | Bold | 32 |
| H4 | 20 | Bold | 28 |
| Body L | 16 | Regular | 24 |
| Body M | 14 | Regular | 22 |
| Caption | 12 | Regular | 18 |
| Label | 12 | Bold | 16 |

## 3.3 Spacing system
- Base unit: **8 px**
- Allowed spacing steps: 8, 12, 16, 24, 32, 40, 48, 64
- Minimum distance between unrelated blocks: 24
- Minimum padding inside cards: 16

---

## 4. Page templates

## 4.1 A4 portrait template (for PRD/API/Sprints)
- Frame: 794 x 1123
- Safe margin: 32 all sides
- Usable content width: 730
- Structure:
  1. top accent strip (6-8 px),
  2. title zone,
  3. section body blocks,
  4. footer line + page meta.

## 4.2 Architecture landscape template
- Frame recommendation: 1600 x 1000 (or 1440 x 900 if bridge stability requires)
- Left-to-right flow architecture with grouped zones:
  - inputs -> core services -> storage -> outputs -> governance.

---

## 5. Component standards

1. Cards:
   - radius 12-14,
   - panel background `bg-panel`,
   - subtle stroke `stroke-soft` (1 px),
   - no heavy shadows.
2. Section dividers:
   - use spacing first, lines second.
3. Tables:
   - header row with low-tint background,
   - fixed column structure per page.
4. Diagrams:
   - use one arrow style and one node style set for consistency.

---

## 6. Anti-overflow and anti-ugliness rules

1. No paragraph may exceed target readable width (~45-85 chars/line practical target).
2. No text may touch card edges; minimum 16 px padding.
3. No orphan headings at page bottom.
4. No mixed alignment in same content group (left-aligned default).
5. No random color usage outside token set.
6. No all-caps for long body lines.
7. No element crowding:
   - if section feels dense, split to next page.
8. Every page must have one dominant focal point only.
9. Decorative shapes allowed only if they support hierarchy.

---

## 7. Quality gates before export

## 7.1 Visual QA
1. Contrast check on all text (WCAG thresholds).
2. Alignment check: left edges, card widths, spacing rhythm.
3. Typography consistency check (no accidental font/style drift).
4. Overflow check on every text block.
5. Pagination logic check: continuous narrative, no abrupt jumps.

## 7.2 Content QA
1. Claims match project facts.
2. API names/fields exactly match `docs/API.md`.
3. Sprint timeline aligns with provided team history.
4. Architecture flows match backend reality.

## 7.3 Export QA
1. Correct page order.
2. File naming consistency.
3. No clipped objects.
4. Final PDF opens fast and renders clean.

---

## 8. Build discipline for this project

1. Build from storyboard first (approved scripts only).
2. Implement one PDF at a time, page by page.
3. Screenshot review checkpoints before final export.
4. Export each PDF separately; no forced merge unless requested.

