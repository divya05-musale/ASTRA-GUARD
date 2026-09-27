# ASTRA-GUARD Documentation Images

This directory contains visual assets used by ASTRA-GUARD documentation and project presentations.

## Purpose

The `images` directory is intended for screenshots, diagrams, and other visual documentation assets.

Typical assets may include:

* System architecture diagrams
* Data-flow diagrams
* Component diagrams
* Live webcam screenshots
* Decision overlay screenshots
* Controlled demo screenshots
* Protocol validation screenshots
* Project presentation images

## Recommended Naming

Use clear and descriptive filenames.

Examples:

```text
system-architecture.png
data-flow.png
component-diagram.png
live-demo.png
correct-decision.png
deviation-decision.png
uncertain-decision.png
protocol-flow.png
```

Avoid filenames such as:

```text
image1.png
final.png
new.png
test.png
screenshot123.png
```

## Image Guidelines

Documentation images should:

* Be directly related to ASTRA-GUARD.
* Have readable text and labels.
* Avoid unnecessary personal information.
* Use reasonable image dimensions.
* Prefer PNG for diagrams and screenshots.
* Use JPG when appropriate for photographs or video frames.

## Architecture Diagrams

Architecture diagrams should clearly communicate the relationship between:

```text
Perception
    ↓
Protocol Integration
    ↓
Mission State
    ↓
Validation
    ↓
Decision Engine
    ↓
Guidance
```

The detailed architecture documentation is available under:

```text
docs/architecture/
```

## Demo Screenshots

Useful demonstration screenshots may include:

### CORRECT

A protocol action is accepted because the detected condition matches the expected protocol condition.

### DEVIATION

A protocol violation is detected, such as:

* Wrong object
* Wrong sequence
* Skipped step
* Unknown action

### UNCERTAIN

The system requests verification when perception confidence is insufficient.

## Privacy

Do not store screenshots containing:

* Passwords
* API keys
* Access tokens
* Personal credentials
* Private documents
* Unnecessary personal information

## Repository Usage

Visual assets stored here can be referenced from Markdown documentation using relative paths.

Example:

```markdown
![ASTRA-GUARD Architecture](../images/system-architecture.png)
```

Keep documentation images small enough for practical repository usage.

Large videos and raw recordings should not be stored in this directory. Use the appropriate project location or external storage when required.

## Current Status

The directory is prepared for future documentation screenshots and diagrams.

The ASTRA-GUARD source code and documentation remain usable without these optional visual assets.

## Summary

```text
docs/images/
    ↓
Screenshots
Diagrams
Demo Evidence
Presentation Visuals
```

This directory supports project documentation, demonstrations, and future presentation material.
