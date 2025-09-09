# Design Tokens (Seed)

This seed provides a neutral, accessible token set for rapid POCs and theming experiments. It complements the Spec Kit’s specification-driven workflow.

- tokens.css — CSS variables for quick application in web UIs
- tokens.json — canonical token export for pipelines and non-CSS consumers

Suggested next steps
- Add a Storybook (html-vite) to preview components and BOCC shell
- Export tokens in multiple formats (CSS, JSON, TS) via a small build script
- Wire a CI check to ensure token changes are reviewed alongside specs
