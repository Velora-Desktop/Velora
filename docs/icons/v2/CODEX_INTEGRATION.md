# CODEX TASK — Integrate Velora Icon Pack v2

1. Read `manifest.json`, `README_RU.md`, and `ICON_USAGE_MAP.md`.
2. Copy the `svg/` tree into the common assets directory without renaming files.
3. Register icons in the existing `IconRegistry`.
4. Do not replace branded platform icons from Icon Pack v1.
5. Replace text/emoji placeholders only where the icon improves readability.
6. Use `currentColor` SVG rendering or the project's existing tint mechanism.
7. Cache QIcon/QPixmap.
8. Provide a fallback for missing icons.
9. Do not change SQLite schemas or business logic.
10. Verify dark theme, hover, selected, disabled and error states.
11. Run syntax/tests and report all changed files.
12. Do not commit automatically.
