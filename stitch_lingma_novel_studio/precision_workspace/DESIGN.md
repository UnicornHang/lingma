---
name: Precision Workspace
colors:
  surface: '#faf8ff'
  surface-dim: '#d6d9eb'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e5e7f9'
  surface-container-highest: '#dfe2f4'
  on-surface: '#171b28'
  on-surface-variant: '#464554'
  inverse-surface: '#2c303d'
  inverse-on-surface: '#eef0ff'
  outline: '#767586'
  outline-variant: '#c6c5d7'
  surface-tint: '#484bd6'
  primary: '#4144cf'
  on-primary: '#ffffff'
  primary-container: '#5b5fe9'
  on-primary-container: '#f7f4ff'
  inverse-primary: '#c0c1ff'
  secondary: '#5b5e6a'
  on-secondary: '#ffffff'
  secondary-container: '#e0e2f0'
  on-secondary-container: '#616470'
  tertiary: '#00662b'
  on-tertiary: '#ffffff'
  tertiary-container: '#008239'
  on-tertiary-container: '#dbffda'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#05006c'
  on-primary-fixed-variant: '#2e2ebe'
  secondary-fixed: '#e0e2f0'
  secondary-fixed-dim: '#c3c6d3'
  on-secondary-fixed: '#181b25'
  on-secondary-fixed-variant: '#434651'
  tertiary-fixed: '#6bff8f'
  tertiary-fixed-dim: '#4ae176'
  on-tertiary-fixed: '#002109'
  on-tertiary-fixed-variant: '#005321'
  background: '#faf8ff'
  on-background: '#171b28'
  surface-variant: '#dfe2f4'
typography:
  display:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style
The design system defines an elite, distraction-free desktop environment engineered for extended deep-work sessions in narrative architecture and computational writing. The design vocabulary balances structural rigor with cognitive calm, ensuring content creators and technical directors retain maximum focus across dense, multi-pane workspaces.

The visual direction draws from **Corporate / Modern** principles with disciplined Swiss-style information architecture:
- **Calm & Precision:** Crisp structural boundaries, controlled optical hierarchy, and deliberate micro-contrast replace decorative trends.
- **Airy Density:** Ample whitespace within functional panels preserves clarity while maintaining professional tooling density.
- **Cognitive Comfort:** Soft neutral backdrops minimize eye fatigue during sustained production hours, utilizing high-clarity sans-serif metrics and monospaced anchors for programmatic entities.

## Colors
The color system operates on an intentional hierarchy calibrated for maximum functional legibility:

- **Primary (`#5B5FE9`):** Represents focused interactive state, primary triggers, and current selection indicators.
- **Primary Light (`#EEF0FE`):** Backing fill for selected states, active navigation rows, and interactive chips.
- **Surface Scale:**
  - Canvas / Background Primary: `#FFFFFF` (document cards, primary editors, actionable modals).
  - Background Secondary: `#F8F9FC` (workspace body container, secondary tool racks).
  - Background Sidebar: `#F4F5F9` (fixed navigation spine and persistent structural side panels).
- **Text Tiers:**
  - Primary (`#1F2330`): High-contrast titles, active copy, and authoritative interface labels.
  - Secondary (`#5C6275`): Metadata, subheaders, structural captions, and inactive icons.
  - Tertiary (`#9CA3B5`): Disabled placeholders, inline hints, and tertiary breadcrumbs.
- **Borders & Dividers:**
  - Border Default: `#E5E7EE` (1px clean structural separators).
  - Border Hover: `#D1D5E0` (interactive target reinforcement).
- **Status Accents:**
  - Success: `#22C55E` (build completion, saved states, operational health).
  - Warning: `#F59E0B` (branch divergences, pending reviews).
  - Danger: `#EF4444` (destructive actions, parse errors, system alerts).

## Typography
The typographic hierarchy is structured around `Inter` for interface elements and narrative readability, complemented by `JetBrains Mono` for programmatic tokens, system variables, entity IDs, and API payload inspection.

- **Display & Headlines:** Tightly tracked headings establish immediate orienting landmarks across large viewport spans.
- **Body & Reading Flow:** Body metrics preserve generous vertical rhythm, critical for high-volume text ingestion and prolonged proofreading.
- **Code & Monospace Rules:** `JetBrains Mono` is reserved strictly for syntax tokens, node variables, schema bindings, and timestamp logs. Never employ monospace styling for standard user interface controls or narrative prose.

## Layout & Spacing
The layout architecture is anchored strictly to an uncompromising 1920×1080 desktop canvas, governed by an exact structural spatial shell:

- **Sidebar Container:** Fixed `240px × 1080px`, rendered with surface `Background Sidebar` (`#F4F5F9`) and a persistent right border (`1px solid #E5E7EE`).
- **Main Workspace Shell:** Fixed width of `1680px`, divided vertically into:
  - **Header Region:** Fixed `1680px × 64px`, pinned at top, bottom-bordered with `#E5E7EE`. Houses breadcrumbs, workspace actions, and global status items.
  - **Content Viewport:** Fixed `1680px × 1016px` inner surface with `Background Secondary` (`#F8F9FC`), padded with `24px` (`space-xl`) outer margins for internal work canvases.
- **Grid & Spacing Scale:** Built upon an absolute 4px base increment:
  - `space-xs` (4px): Micro-gaps between icons and paired text labels.
  - `space-sm` (8px): Form input inner vertical padding and compact list element spacing.
  - `space-md` (12px): Standard inline component spacing and toolbar groups.
  - `space-lg` (16px): Card internal padding and default grid gutter separation.
  - `space-xl` (24px): Primary panel margins and section breaks.
  - `space-2xl` (32px): Major module segregation across the active 1016px viewport.

## Elevation & Depth
Depth in the design system is achieved primarily through **low-contrast outlines** and **tonal layering**, rather than heavy dimensional drop-shadows. This preserves crisp visual alignments suited for precision software.

- **Level 0 (Base Canvas):** Background surfaces (`#F8F9FC` and `#F4F5F9`) sit flush at `z-index: 0`.
- **Level 1 (Card & Module Shells):** Pure white surfaces (`#FFFFFF`) framed by a single hairline border (`1px solid #E5E7EE`). Shadows are used sparingly; when elevated on hover, apply an ultra-diffused ambient shadow: `box-shadow: 0 1px 3px 0 rgba(31, 35, 48, 0.04), 0 1px 2px -1px rgba(31, 35, 48, 0.02)`.
- **Level 2 (Popovers & Flyouts):** Dropdowns, context menus, and tool palettes leverage: `box-shadow: 0 4px 12px rgba(31, 35, 48, 0.08)`, bounded by a `1px solid #E5E7EE` border.
- **Level 3 (Modal Dialogs):** Centered modal overlays carry a focused shadow: `box-shadow: 0 12px 32px rgba(31, 35, 48, 0.12)`, backed by an unobtrusive scrim `rgba(31, 35, 48, 0.35)`.

## Shapes
The system relies on a refined, low-curvature geometric profile (Level 1 / Soft) reflecting high-precision desktop software:

- **`radius-sm` (4px):** Checkboxes, code tag pills, secondary micro-badges, and inline metadata pills.
- **`radius-md` (6px):** Form inputs, buttons, menu list items, tab segments, and compact list selections.
- **`radius-lg` (8px):** Primary panel cards, preview panes, floating inspection sheets, and modular grid cells.
- **`radius-xl` (12px):** Modal windows, global workspace flyouts, and floating contextual command bars.
- **`pill` (9999px):** Status badges, count chips, and avatar indicators.

## Components

### Buttons
- **Primary:** Background `#5B5FE9`, text `#FFFFFF`, radius `6px`. Hover state: `#4B4FD9`. Active state: `#3F43C7`. Padding: `8px 16px` (`label-md`).
- **Secondary:** Background `#FFFFFF`, text `#1F2330`, border `1px solid #E5E7EE`, radius `6px`. Hover state: background `#F8F9FC`, border `#D1D5E0`.
- **Ghost:** Transparent background, text `#5C6275`. Hover state: `#EEF0FE` fill with `#5B5FE9` text.
- **Destructive:** Background `#EF4444`, text `#FFFFFF`, radius `6px`. Hover state: `#DC2626`.

### Inputs & Selectors
- Background `#FFFFFF`, border `1px solid #E5E7EE`, text `#1F2330`, border radius `6px`, vertical height fixed at `36px`, horizontal padding `12px`.
- **Hover:** Border shifts to `#D1D5E0`.
- **Focus:** Border shifts to `#5B5FE9`, ring: `0 0 0 3px #EEF0FE`.
- **Code Inputs:** Rendered using `JetBrains Mono` (`code-md`), surface `#F8F9FC`, border `#E5E7EE`.

### Checkboxes & Radios
- Size: `16px × 16px`. Default state: border `1.5px solid #D1D5E0`, background `#FFFFFF`, radius `4px` (checkbox) or `9999px` (radio).
- Selected state: background `#5B5FE9`, border `#5B5FE9`, with white indicator icon.

### Chips & Badges
- **Status Badges:** Height `22px`, radius `9999px`, padding `2px 8px`. Success: background `#DCFCE7`, text `#15803D`. Warning: background `#FEF3C7`, text `#B45309`. Danger: background `#FEE2E2`, text `#B91C1C`.
- **Interactive Filter Chips:** Radius `6px`, height `28px`, padding `4px 10px`, background `#FFFFFF`, border `1px solid #E5E7EE`. Active state: background `#EEF0FE`, text `#5B5FE9`, border `#5B5FE9`.

### Cards & Panels
- Canvas: `#FFFFFF`, border `1px solid #E5E7EE`, radius `8px`.
- Card Header: `16px` padding, bottom border `1px solid #E5E7EE`, headline `headline-sm`.
- Card Body: `16px` interior padding.

### Navigation Lists (Sidebar Items)
- Height: `36px`, radius `6px`, margin `2px 12px`, padding `0 12px`.
- Default: Text `#5C6275`, transparent background.
- Hover: Text `#1F2330`, background `rgba(31, 35, 48, 0.04)`.
- Active: Text `#5B5FE9`, background `#EEF0FE`, font weight `500`. Accent marker: vertical bar `3px × 16px` `#5B5FE9` at outer left edge.