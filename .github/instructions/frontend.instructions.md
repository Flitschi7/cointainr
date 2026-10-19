---
description: "Use for Cointainr Svelte components, frontend services, styling, and browser tests."
applyTo: "frontend/**"
---

# Frontend

## Behavior

- Follow the existing Svelte conventions in the touched component; keep framework
  migrations separate from behavior fixes.
- Trace routes through stores and services before changing request/caching logic.
  Preserve cache freshness, stale indicators, manual refresh, and offline fallback.
- Preserve currency units and purchase currency. Distinguish unavailable values
  from zero; a raw foreign amount is not a converted amount.
- Use `import.meta.env.DEV` for development-only code. Expose only intentionally
  public configuration; keep the host process environment out of client bundles.
- Guard browser-only APIs during SSR; clean up subscriptions, timers, and charts.
- Reuse existing unit suites with mocked network calls and controlled time.
  Check `package.json` and Playwright configuration before selecting commands.

## Design

Preserve the established quiet, dark, information-dense portfolio interface.
Reuse components and semantic tokens rather than restyling unrelated views.

| Token        | Color     | Purpose                     |
| ------------ | --------- | --------------------------- |
| `primary`    | `#00C896` | Main actions and highlights |
| `background` | `#1E1E2F` | App background              |
| `surface`    | `#2A2F45` | Panels and modals           |
| `text-light` | `#F0F4F8` | Body text                   |
| `profit`     | `#2ECC71` | Positive financial change   |
| `loss`       | `#E74C3C` | Negative financial change   |
| `gold`       | `#D4AF37` | Coin emphasis               |

Use Inter for body/navigation, Space Grotesk for headings, and JetBrains Mono
for technical values. Reuse existing font loading; avoid adding external requests.
Keep profit/loss legible without relying on color alone. Verify keyboard access,
focus, loading/error states, and mobile overflow for changed views.
