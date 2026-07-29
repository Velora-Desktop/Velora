# Velora AW0.22

- Python 3.12.13, PySide6 6.11.1, UTF-8, Windows.
- Follow the approved UX; do not redesign or add unrequested features.
- Keep UI modular and use Qt layouts instead of absolute page positioning.
- Before creating any new UI component, verify whether the required behavior
  can be implemented by extending an existing component. Create a new
  component only when reuse would complicate the architecture or reduce code
  readability.
- Overloaded, outdated, or illogical UI elements may be reworked during
  implementation only when their existing functionality is preserved and the
  result follows the AW0.21 product philosophy. List every such rework in the
  final report with a short rationale.
- Treat AW0.21 as one cohesive product release rather than a collection of
  isolated features:
  - keep new UI visually consistent, uncluttered, and aligned with the shared
    application style;
  - avoid duplicated components and design reusable game-card components;
  - before accepting a solution, verify that another game can use it without
    game-specific code changes; otherwise propose a more universal design;
  - follow the existing code style, avoid unnecessary architecture, and mark
    every unavoidable temporary solution explicitly;
  - placeholders must look like finished product states, not empty screens;
  - document every architectural or UX decision that differs from the
    approved specification, with its rationale, in the final report.
- The AW0.21 quality gate prioritizes coherent UX, reusable architecture, and
  future Games UI scalability over the number of implemented features. Doom
  Eternal is the reference card, not a source of one-off UI behavior.
- Preserve Velora's independent product identity. Do not design the reference
  card to imitate Steam, IGDB, Backloggd, or another existing service. Apply
  proven UX practices only through Velora's own navigation logic, visual
  language, and interaction model.
- For the AW0.21 reference-card work, do not change Schema 1, Contracts,
  repositories, Unit of Work, application services, the existing Journey
  backend, playthrough history, or the approved vertical slice. Journey UI is
  a read model over existing data; do not create a second Journey, schema, or
  backend.
- Prefer universal `Game*` components over Doom-specific components. Validate
  them against structurally different games such as GTA VI, Escape from
  Tarkov, Euro Truck Simulator, Forza Horizon, and Minecraft.
- The final AW0.21 report must identify full UI reworks, UX decisions, new and
  reused components, universal patterns, Creator-ready elements, and any
  justified improvements beyond the initial specification.
- AW0.21 product philosophy:
  - Velora is the user's personal gaming history, not merely a game catalog;
  - design every screen around what the user feels, remembers, or decides,
    rather than around the maximum amount of data that can be displayed;
  - Journey is a memory of a playthrough, not a mission log;
  - a game page is a living, interactive, comfortable personal space, not a
    reference encyclopedia;
  - statistics should motivate and tell a story, never resemble a spreadsheet;
  - show only information that helps a decision or brings back a memory;
  - prefer breathing room and clear hierarchy over information density;
  - placeholders should communicate a credible future capability rather than
    unfinished work;
  - reuse existing subtle micro-animations where appropriate, but do not add
    heavy visual effects;
  - design every component for long-term reuse and maintenance.
- Before accepting any AW0.21 screen, ask whether a first-time user would want
  to continue using Velora after seeing it. If not, improve the screen without
  crossing the frozen architectural boundaries.
- User-facing text is Russian; Python identifiers are English.
- Unfinished actions use the shared placeholder dialog.
- SQLite is allowed for the separated official catalog and future local user data.
- Do not commit automatically.
