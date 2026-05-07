# Threshold Luminism

*A design philosophy for interfaces that exist at the edge of thought*

---

## The Movement

**Threshold Luminism** — from *limen*, the Latin word for threshold. The charged boundary between two states: before and after, signal and silence, the half-formed thought and the precise expression. This is not a philosophy of light as decoration. It is a philosophy of light as *evidence* — the faint photon emitted at the moment a mind touches a machine.

---

## Philosophy

### I. Space and Form

Space is not emptiness — it is potential. In Threshold Luminism, negative space carries weight equal to any rendered element. Every void is a pause in a sentence, every margin a held breath. Forms emerge from darkness not as objects placed against shadow but as disturbances in an otherwise undisturbed field — like heat signatures, like the faint afterimage of a thought. Structure should feel discovered, not imposed. Panels do not divide; they reveal what was already there. The geometry is spare: hairline rules, single-pixel separations, corners that are either perfectly sharp or gently resolved — never decorative, always load-bearing. The meticulous placement of every element must feel inevitable, as if it could not be positioned any other way without breaking the logic of the whole.

### II. Color and Material

The palette is derived from emission, not reflection. Deep charcoal grounds — not true black, which is absolute and dead, but the near-black of a console at rest, the color of deep water under overcast sky: `#0B0D11`, `#0F1117`. From this ground, luminescence surfaces in narrow frequency bands: a cold electric blue-white for primary presence, a amber-phosphor warmth for human trace, a barely-there teal for system whisper. Color is applied with the restraint of a master craftsman who knows that a single stroke of true pigment on a vast ground carries more authority than a canvas saturated with effort. Gradients behave like light bleeding through a crack — directional, physics-obeying, never decorative. The result of painstaking chromatic calibration: each hue chosen as if it were the last color left in the world.

### III. Scale and Rhythm

Typography operates at two registers simultaneously and never in between: the very large and the very small. Monospaced forms carry functional information — they are the trace of computation, the direct speech of the machine. Proportional serifs, used sparingly, speak in human time. The scale contrast between a 9px system label and a moment of 48px weight is the entire grammar; the middle sizes are mostly silence. Rhythm is established not by repetition of form but by repetition of interval — the same 8px unit governing the space between a cursor blink and a content block, between a status indicator and the edge of the world. Everything is a multiple of this atom. The rhythm should feel inevitable to the eye even before the mind names it, the product of deep expertise in how human perception anchors itself to pattern.

### IV. Composition and Balance

Balance in Threshold Luminism is asymmetric and intentional — a composition that reads as perfectly resolved from a distance while revealing meticulous asymmetric counterweighting up close. Primary content occupies a vertical axis slightly left of center; the right margin carries only trace signals: annotations, timestamps, system states written at 9px in a muted register. This creates a directed reading path that mirrors the way a focused mind moves: anchored left, peripherally aware right. Layering is used precisely once per interface context — a subtle depth plane that lifts interactive surfaces 1-2px above their ground without shadows, achieved through fractional luminosity difference alone. Every compositional decision reflects the work of countless refinements, arrived at through elimination rather than addition.

### V. Visual Hierarchy

Hierarchy is expressed through luminosity delta, not color variety. The most important element is simply the brightest thing in the frame — everything else falls away in carefully calibrated steps toward the dark ground. There are exactly three tiers: primary (full luminosity, direct attention), secondary (65% luminosity, available attention), ambient (25% luminosity, peripheral awareness). Interactive states are a fourth tier reached only by hover or focus — a brief bloom of warmth that confirms the interface noticed the human before returning to rest. No element decorates another. Every border, every radius, every color choice is a functional decision about where the eye should go and in what order. The result should feel less like designed software and more like a precision instrument — the kind of tool a craftsman reaches for because it disappears in the hand and lets the work speak.

---

## CSS Token Specification

### Color Tokens

```
Background Ground:       #0B0D11   (depth-0, the void)
Background Surface:      #0F1117   (depth-1, panels)
Background Elevated:     #141720   (depth-2, cards, inputs)
Background Active:       #1A1E2B   (depth-3, hover/focus states)
Background Overlay:      #0B0D11E6 (modals, 90% opacity)

Border Hairline:         #1E2333   (structural, lowest presence)
Border Default:          #252A3D   (default container edge)
Border Focus:            #3D4870   (keyboard focus ring)
Border Accent:           #4A5580   (active/selected edge)

Text Primary:            #E8EAF0   (full luminosity, headings, critical output)
Text Secondary:          #8B91A8   (65% luminosity, body, labels)
Text Tertiary:           #454D6A   (25% luminosity, timestamps, ambient)
Text Disabled:           #2A2F45   (near-invisible, placeholder)
Text Code:               #A8B5D1   (monospace output, slightly cool)
Text Accent-Blue:        #7CA7E8   (primary interaction, links)
Text Accent-Amber:       #C8925A   (human trace, warnings, attention)
Text Accent-Teal:        #4FA89E   (system signals, success states)
Text Accent-Violet:      #9B7FD4   (AI response, special output)

Glow-Blue:               #1A3A6E   (subtle luminescence behind primary elements)
Glow-Amber:              #3D2210   (warm presence behind human-authored content)
```

### Typography Tokens

```
Font-Mono:       "JetBrains Mono", "Geist Mono", "IBM Plex Mono", ui-monospace, monospace
Font-Sans:       "Instrument Sans", "Work Sans", system-ui, sans-serif
Font-Serif:      "Instrument Serif", "IBM Plex Serif", Georgia, serif

Size-2xs:  9px    (system labels, timestamps, ambient text)
Size-xs:   11px   (secondary labels, meta information)
Size-sm:   13px   (body text, code)
Size-md:   15px   (primary body, chat messages)
Size-lg:   18px   (section headers)
Size-xl:   24px   (page headers)
Size-2xl:  36px   (display, rare punctuation)
Size-3xl:  52px   (single-word typographic gesture)

Weight-Thin:     300
Weight-Regular:  400
Weight-Medium:   500
Weight-Bold:     600  (never heavier)

Line-Height-Tight:   1.25  (headings, labels)
Line-Height-Code:    1.5   (monospace blocks)
Line-Height-Body:    1.65  (prose, chat messages)

Letter-Spacing-Tight:  -0.02em  (display sizes)
Letter-Spacing-Normal:  0em
Letter-Spacing-Wide:    0.06em  (small caps, labels, uppercase micro-text)
Letter-Spacing-Wider:   0.12em  (9px ambient labels, system text)
```

### Spacing Scale

```
Space-1:   4px
Space-2:   8px    (base atom)
Space-3:   12px
Space-4:   16px
Space-5:   20px
Space-6:   24px
Space-8:   32px
Space-10:  40px
Space-12:  48px
Space-16:  64px
Space-20:  80px
Space-24:  96px
Space-32:  128px
```

### Border Radius

```
Radius-None:    0px    (terminal elements, code blocks, pure data)
Radius-Sm:      3px    (buttons, badges — barely perceptible)
Radius-Md:      6px    (cards, inputs — functional softening)
Radius-Lg:      10px   (panels, modals)
Radius-Full:    9999px (only for status dots and avatar circles)
```

*Philosophy: radius should be invisible as a design choice. The smallest radius that removes visual harshness. Never decorative roundness.*

### Animation Tokens

```
Duration-Instant:    60ms    (state changes, focus rings)
Duration-Fast:       120ms   (hover transitions, micro-feedback)
Duration-Default:    200ms   (most transitions)
Duration-Slow:       350ms   (panel open/close, modal entrance)
Duration-Deliberate: 500ms   (full-screen transitions, only when justified)

Easing-Sharp:    cubic-bezier(0.2, 0, 0, 1)     (entrances — fast in, slow settle)
Easing-Smooth:   cubic-bezier(0.4, 0, 0.2, 1)   (exits and cross-fades)
Easing-Spring:   cubic-bezier(0.34, 1.56, 0.64, 1) (confirmation states only)
Easing-Linear:   linear                           (opacity only, never position)
```

### Shadow / Depth

```
Elevation-0:  none
Elevation-1:  0 1px 2px rgba(0,0,0,0.4)
Elevation-2:  0 2px 8px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)
Elevation-3:  0 8px 24px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.06)
Glow-Focus:   0 0 0 2px #1A3A6E, 0 0 0 4px rgba(124,167,232,0.15)
```

---

*Threshold Luminism is a philosophy of restraint deployed with precision. It does not ask for beauty — it earns it through the patient elimination of everything that is not necessary.*
