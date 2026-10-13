---
name: CyberScope presentation
description: Bold editorial research slides for projected IoT integrity explanation.
colors:
  paper: "#f4f1e9"
  ink: "#20231f"
  muted: "#60645b"
  line: "#d2d3c8"
  cobalt: "#214be0"
  teal: "#08766b"
  red: "#c43e2d"
  blue-wash: "#e6ebfc"
  teal-wash: "#e2eee5"
  red-wash: "#f8e7df"
typography:
  display:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "68px"
    fontWeight: 700
    lineHeight: 1.04
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "51px"
    fontWeight: 500
    lineHeight: 1.14
    letterSpacing: "-0.035em"
  statistic:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "136px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.04em"
  body:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "24px"
  diagram-title:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "19px"
    fontWeight: 500
  diagram-detail:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "15px"
    fontWeight: 400
  control:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "16px"
rounded:
  navigation: "4px"
  control: "6px"
  compact-node: "9px"
  node: "12px"
  zone: "16px"
spacing:
  compact: "12px"
  standard: "24px"
  slide-gutter: "68px"
components:
  motion-toggle:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  motion-toggle-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  navigation-button:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.navigation}"
    padding: "6px"
  navigation-button-hover:
    backgroundColor: "{colors.blue-wash}"
  diagram-node:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.node}"
  diagram-node-match:
    backgroundColor: "{colors.teal-wash}"
    textColor: "{colors.ink}"
  diagram-node-mismatch:
    backgroundColor: "{colors.red-wash}"
    textColor: "{colors.ink}"
---

# Design System: CyberScope presentation

## Overview

**Creative North Star: "The Projected Research Editorial"**

CyberScope uses a bold editorial research presentation: warm paper, dark typography, large evidence and precise vector flows. Its density supports university projection, with enough structure to trace device state through hashing, comparison and an explicit outcome.

The system is flat and deliberate. Cobalt links the editorial voice to the integrity path; teal and vermilion distinguish acceptance and changed state. Motion explains a sequence and remains under presenter control.

**Key Characteristics:**
- Oversized editorial headings and tabular statistics.
- Flat, outlined vector nodes and routed connections.
- Named outcomes alongside semantic color.
- A fixed widescreen canvas with keyboard navigation and motion control.

## Colors

Warm paper and near-black anchor the editorial voice; saturated accents carry integrity and outcome meaning. The frontmatter preserves the implementation's color names and values.

### Primary
- **Cobalt:** Headline emphasis, statistics, hash generation, onboarding, baseline paths, active phase and progress.
- **Blue wash:** Attestation-agent surface and navigation hover.

### Secondary
- **Teal:** Sensor pathways and accepted outcomes.
- **Teal wash:** Accepted-result surfaces and sensor packets.

### Tertiary
- **Vermilion (red):** Changed-device origin, mismatches, rejected readings and alerts.
- **Red wash:** Tampering and rejected-result surfaces.

### Neutral
- **Paper:** Slide background and ordinary diagram-node surfaces.
- **Ink:** Main copy, structural rules, administrator surface and control strokes.
- **Muted:** Supporting labels, source text, navigation count and inactive phases.
- **Line:** Diagram-node outlines, evidence dividers and inactive ledger bars.

**The Outcome Rule.** Pair acceptance and rejection colors with explicit labels or icons; color alone does not carry the decision.

## Typography

**Display and Body Font:** Space Grotesk, locally bundled, with sans-serif fallback.
**Technical Font:** Monospace for digest strings and comparisons.

The type is direct and compact, with tight headline tracking and tabular statistics. Display, headline, statistic and recurring diagram roles are recorded in the frontmatter. The methodology title has an observed local size adjustment (54px); evidence explanations, annotations and diagram captions adapt to their specific spatial role rather than creating another global type scale.

## Layout

The deck uses a fixed canvas (1600 × 900). The problem slide uses padding (54px 68px 40px) and two equal columns with a gap (66px). The methodology slide uses wider local composition with padding (34px 32px 40px); its SVG follows its intrinsic ratio (1536 × 550) at full available width, without a height cap or side letterboxing. Each slide’s header and footer rules align to its own side gutters. Footers are anchored above the viewport navigation.

**The Canvas Rule.** Preserve the complete 16:9 slide at smaller viewports; scale the composition as a preview rather than reflowing it into an article.

Reveal scales the canvas with a margin (0.02), minimum scale (0.1) and maximum scale (2). At the phone breakpoint (600px), viewport navigation moves closer to the corner; slide content retains its widescreen composition.

## Elevation & Depth

There are no shadows. Depth comes from outlined nodes, pale semantic fills, nested zones and a dark administrator node. Result fills appear only after comparison; subdued paths become fully visible when their outcome is active.

## Shapes

Editorial rules and evidence dividers remain straight. Diagram nodes use gently rounded rectangles, with smaller radii for compact nodes and broader zone boundaries. Hash generation uses a circle and dotted orbit. Small inline SVG icons share rounded stroke ends rather than glyph substitutes.

## Components

### Buttons

The motion control is a compact outlined rectangle with an inline SVG and text. Its transparent resting surface inverts to ink and paper on hover. Pause and resume update both the visible label and accessible pressed state. Focus uses a cobalt outline (3px) with offset (5px).

### Navigation

Viewport navigation uses small arrow buttons, a tabular slide count and a transparent surface. Enabled arrows gain a blue-wash hover; unavailable arrows reduce opacity (0.3) and remain disabled. Keyboard focus uses the shared outline. Phase navigation within the scenario strip uses a cobalt underline and ink text for the active stage, with muted inactive stages.

### Evidence rows

Repeated rows pair oversized cobalt numerals with a short explanation, separated by line-colored rules. Numerals retain tabular figures; the percentage sign is subordinate to the main number.

### Diagram nodes

Ordinary nodes use paper and line-colored outlines. The attestation agent uses blue wash; baseline boundaries use cobalt; sensor paths use teal. Accepted and rejected nodes keep their explicit label and icon as the wash and border change. Node-state transitions use the shared easing over 0.4 seconds. Outcome nodes use compact rectangles (240px × 75px for acceptance) with main labels (18px). The sensor-data consumer is a labeled node; alerts route around the outside right and top edges, avoiding the consumer flow.

The illustrative loop runs for 30 seconds: onboarding, unchanged runtime, changed runtime and approved restoration. Nodes remain fixed while repeated data streams travel at a shared distance-based speed (90 SVG units per second), using cached 160-point path interpolation and smooth endpoint fades. A quiet glyph cloud supports the hash generator. It pauses when the slide is inactive, the document is hidden or the presenter pauses it. Reduced motion hides moving packets and removes transitions while retaining narrated states.

## Do's and Don'ts

### Do:
- **Do** use the shared palette and Space Grotesk hierarchy.
- **Do** keep arrows, labels and diagram outcomes visually distinct.
- **Do** provide keyboard focus, pause/resume and reduced-motion behavior.
- **Do** preserve projector composition when previewing on a portrait phone.

### Don't:
- **Don't** replace the precise vector diagrams with decorative imagery.
- **Don't** communicate a match or mismatch through color alone.
- **Don't** introduce shadows or ornamental surfaces into this flat editorial system.
