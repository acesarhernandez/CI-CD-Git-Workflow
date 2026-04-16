# CI/CD Git Workflow

A reusable, manifest-driven CI/CD system for building, deploying, verifying, and recovering applications using GitHub Actions and self-hosted runners.

---

## What this is

This repository contains a **shared CI/CD engine** designed to be reused across multiple applications.

Instead of duplicating CI/CD logic in every app, this system centralizes:

- build and publish
- deployment
- verification
- recovery
- policy and validation

Applications integrate with this system using thin wrapper workflows.

---

## Key Features

- Reusable GitHub Actions workflows
- Manifest-driven deployments
- Built-in verification step
- Release retention for recovery
- Recovery from previous releases
- Self-hosted runner support
- Schema-based configuration validation

---

## How it works

1. App repo triggers workflow
2. Shared workflows handle:
   - validation
   - build/publish
   - deploy
   - verify
3. A release manifest is generated and retained
4. Recovery can later use that manifest

---

## Repository Structure

.github/workflows/ → reusable workflow engine
scripts/ → Python logic
schemas/ → validation schemas
docs/ → onboarding + troubleshooting

---

## Getting Started

To integrate an app with this system:

👉 See the onboarding guide:  
`docs/onboarding-guide.md`

---

## Recovery

Releases are retained on the deployment host and can be recovered using:

- retained release manifest
- manual recovery workflow

---

## Status

This system has been fully validated with a real application (DeskSim), including:

- full deployment lifecycle
- manifest retention
- recovery workflow
- self-hosted runner execution

---

## Notes

This system is designed to be:

- reusable
- predictable
- debuggable
- AI-assisted (via structured docs and prompts)
