# ASTRA-GUARD Documentation

This directory contains the technical and project documentation for ASTRA-GUARD.

ASTRA-GUARD is an academic prototype for onboard monitoring and protocol validation using computer vision, hand tracking, protocol-aware perception, and deterministic decision logic.

## Documentation Structure

```text
docs/
├── README.md
│
├── architecture/
│   ├── system-architecture.md
│   ├── component-diagram.md
│   └── data-flow.md
│
├── development/
│   ├── setup.md
│   └── development-guide.md
│
├── experiment/
│   ├── experiment-protocol.md
│   ├── deviation-rules.md
│   └── dataset-documentation.md
│
├── deployment/
│   └── deployment-guide.md
│
├── demo/
│   └── demo-guide.md
│
└── images/
    └── README.md
```

## Architecture

The architecture documentation explains how the major ASTRA-GUARD components interact.

### System Architecture

`architecture/system-architecture.md`

Describes the overall system architecture, including perception, protocol integration, mission state, validation, decision making, and guidance.

### Component Diagram

`architecture/component-diagram.md`

Describes the major software components and their responsibilities.

### Data Flow

`architecture/data-flow.md`

Explains how information moves from webcam perception through protocol validation to the final decision.

## Development

### Setup Guide

`development/setup.md`

Provides instructions for installing dependencies, preparing the Python environment, running tests, and starting the project.

### Development Guide

`development/development-guide.md`

Explains the internal implementation structure, development workflow, testing approach, protocol integration, and extension points.

## Experiment

### Experiment Protocol

`experiment/experiment-protocol.md`

Documents the synthetic `EXP001 - TARDIGRADE` demonstration protocol and its sequence of experimental steps.

### Deviation Rules

`experiment/deviation-rules.md`

Documents how ASTRA-GUARD identifies protocol deviations and produces `CORRECT`, `DEVIATION`, or `UNCERTAIN` decisions.

### Dataset Documentation

`experiment/dataset-documentation.md`

Documents the synthetic protocol configuration, perception inputs, object mappings, and validation data used by the prototype.

## Deployment

### Deployment Guide

`deployment/deployment-guide.md`

Describes local deployment, dependency installation, model requirements, runtime verification, camera setup, and deployment limitations.

## Demonstration

### Demo Guide

`demo/demo-guide.md`

Provides the recommended demonstration procedure for:

* Controlled protocol validation
* CORRECT decisions
* DEVIATION detection
* UNCERTAIN handling
* Live webcam perception
* Presentation preparation
* Demo troubleshooting

## Images

`images/README.md`

Documents the purpose and recommended organization of screenshots, diagrams, and other visual documentation assets.

## Main Project Documentation

The repository root contains the primary project overview:

```text
README.md
```

The root README provides:

* Project overview
* Key capabilities
* System flow
* Technology stack
* Running instructions
* Testing information
* Project structure
* Prototype limitations
* Future development

## Recommended Reading Order

For a new reviewer, the recommended order is:

```text
1. Root README
       ↓
2. System Architecture
       ↓
3. Data Flow
       ↓
4. Experiment Protocol
       ↓
5. Deviation Rules
       ↓
6. Demo Guide
       ↓
7. Development / Deployment Guides
```

## Prototype Boundary

ASTRA-GUARD is an academic research and demonstration prototype.

The included `EXP001 - TARDIGRADE` protocol is synthetic and is not an official ISRO flight procedure or proprietary operational protocol.

The current perception system uses a generic YOLO model, MediaPipe hand tracking, deterministic protocol-aware mapping, and rule-based decision logic.

The current prototype does not use an LLM for activity interpretation or decision making.

## Documentation Status

The documentation covers the current implemented prototype, including:

* System architecture
* Data flow
* Component structure
* Protocol definition
* Deviation handling
* Dataset/configuration
* Development setup
* Deployment
* Demonstration procedure
* Documentation assets

## Quick Navigation

```text
Project
│
├── README.md
│
└── docs/
    │
    ├── Architecture
    ├── Development
    ├── Experiment
    ├── Deployment
    ├── Demo
    └── Images
```

This documentation structure is intended to make ASTRA-GUARD easier to understand, reproduce, demonstrate, and extend.
