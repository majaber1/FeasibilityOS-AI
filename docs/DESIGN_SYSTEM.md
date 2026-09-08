# Design System

## Color Palette

### Brand (Saudi-inspired green)
- `brand-50` to `brand-900`: Primary green palette
- Used for: CTAs, active states, navigation highlights

### Gold (Premium accent)
- `gold-50` to `gold-800`: Gold/amber accent
- Used for: Premium features, investor sections, highlights

### Ink (Neutrals)
- `ink-500` to `ink-900`: Text and UI grays
- Used for: Body text, labels, borders

## Typography

- **Latin**: Inter (variable weights)
- **Arabic**: Tajawal (300, 400, 500, 700, 800)
- Language-aware switching via `html:lang()` selector

## Components

### Layout
- `ServiceHeader` — Page header with icon, title, breadcrumb, actions
- `ServiceCard` — Tool/service card with icon, code, status
- `KpiCard` — Key metric display card

### Feedback
- `Badge` — Status/category labels (success, warning, danger, info, neutral, brand, gold)
- `Alert`, `LoadingState`, `ErrorState`
- `Button`
- `Input`, `Select`, `TextArea`, `Field`
- `ContextBanner`, `ImportSource` — explicit optional linking, never silent merge

### Shadows
- `shadow-card`: Subtle resting shadow
- `shadow-card-hover`: Elevated hover shadow

## Design Principles

1. **Generous whitespace**: `py-8` to `py-16` section spacing
2. **Clear hierarchy**: Size + weight differentiate heading levels
3. **Professional cards**: `rounded-2xl border shadow-card` pattern
4. **Restrained gradients**: Only for hero/premium sections
5. **Hover elevation**: `-translate-y-0.5 shadow-card-hover` pattern
6. **RTL-aware**: `rtl:` prefix and logical properties throughout
