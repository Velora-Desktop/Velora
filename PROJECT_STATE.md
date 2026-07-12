# Velora project state

- Version: AW0.02 (Alpha Windows 0.02)
- Python: 3.12.13
- PySide6: 6.11.1

## Completed

- Modular application startup.
- Maximized main window and dark responsive layout.
- Top navigation and overlay V menu.
- Scrollable game-category sidebar with fixed actions.
- Test catalog grouped into first-person and third-person shooters.
- Local title filtering, row selection, favorite toggling.
- Closable Quick View.
- Shared placeholder dialog and basic shortcuts.
- AW0.02 visual system based on `2 кон ред.png`.
- Compact header, category counters and concept-aligned controls.
- Color-coded scores and statuses.
- Three-section Quick View with metadata, ratings, notes and activity.
- Photoshop correction pass: proper favorite stars, clean cover placeholders, no horizontal Sidebar artifacts, and Quick View close button anchored at the upper-right.
- Working local search, pagination, filters and per-group column sorting.
- Collapsible first-person and third-person groups with database-derived counters.
- Interactive favorites and adaptive game statuses.
- Criteria-based personal rating with arithmetic-mean calculation.
- Total playtime editing and timestamped interaction chronology.
- General back/forward navigation history for categories, games and detail transitions.
- Age-rating column and locally persisted 18+ content filtering.
- Functional V menu with settings, about, changelog, Boosty support and exit.
- Local privacy statement and author credits.

## Placeholder only

- Films, series, global search, custom sections, My Velora.
- Full game detail page, films, series, global search, custom sections and My Velora.

## Next planned step

- Start AW0.03 from the stable AW0.02 tag.

## Known limitations

- No database or persistence.
- User-facing settings persist through QSettings; catalog/user records are still in-memory test data.
- No real cover assets or final SVG icon set; neutral placeholders are intentional.
- Pagination is visual only.

## Do not break

- V menu overlays rather than shifting content.
- First-person and third-person catalog grouping.
- Star click does not select the row.
- Row click selects and opens Quick View.
- Quick View closes without clearing the selected row.
- No plus buttons beside individual categories.
- White annotations from the concept image are comments, not UI elements.
