---
name: Linear Geek Style
description: A dark, sleek, professional design system for desktop tools, inspired by Linear's UI.
tokens:
  colors:
    background:
      primary: "#0B0B0C"      # Deep slate black background
      secondary: "#161618"    # Slightly lighter charcoal for panels/cards
      active: "#252529"       # Active state background
    brand:
      primary: "#5e6ad2"      # Linear Purple / Royal Purple
      hover: "#707ee6"        # Slightly lighter purple for hover
      active: "#4d58b2"       # Darker purple for active click
    neutral:
      primary: "#f4f4f5"      # Near-white text
      secondary: "#a1a1aa"    # Muted grey text
      tertiary: "#71717a"     # Darker grey for subtitles/placeholders
      border: "#27272a"       # Sleek thin dark border
    success:
      primary: "#4ade80"      # Muted bright green
      background: "#142c1e"
    error:
      primary: "#f87171"      # Red/rose
      background: "#351616"
  typography:
    family:
      sans: "Segoe UI, Inter, System-UI, sans-serif"
    sizes:
      title: 22
      subtitle: 13
      body: 13
      button: 14
      small: 11
  borders:
    radius:
      base: 8                 # Rounded corner base size
      large: 12
    width:
      base: 1
---

# Visual Design Guidelines

## Visual Identity & Theme
This design system adapts the Linear-style "Developer/Geek" dark mode aesthetic to a desktop environment:
- **Base Canvas**: A very dark slate background (`#0B0B0C`) providing high contrast for text and vibrant accents.
- **Sectioning**: Panels, lists, and form areas use card modules with a slightly lighter background (`#161618`) and a crisp 1px border (`#27272A`).
- **Brand Focus**: A signature royal violet/purple color (`#5E6AD2`) denotes the primary call-to-action buttons.

## Layout Configuration
- **Header**: Clean, modern, text-based branding. Bold white title text with a thin grey description.
- **Scroll List**: Large rounded corner list area. Individual files inside the scrollable container should be represented as distinct visual list cards with hover feedback.
- **Buttons**:
  - Primary button: Solid purple with white text.
  - Secondary button: Outline or dark background with light text.
  - Danger/Delete buttons: Subtle soft red tones or text-based icons.
