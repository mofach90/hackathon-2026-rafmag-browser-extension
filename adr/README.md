# Architecture Decision Records

This folder records the **load-bearing technical decisions** for this project — the ones that would cost real time/money to change later.

## Why ADRs

Months from now, when someone (you included) asks *"why did we pick Firestore?"*, the answer should be one click away, not a guess. ADRs make the *why* permanent — not just the *what*.

## What belongs here vs in `brainstorming/`

- **`brainstorming/`** is exploration — open questions, ideas being weighed, things still in flux. Edit it freely.
- **`adr/`** is the commitment — once a decision is made, it gets an ADR. ADRs are **append-only**: you don't rewrite an old ADR when you change your mind, you write a new one that says *"supersedes ADR-000X"*.

A useful rule of thumb: **if changing the decision would take more than a day to undo, write an ADR**. If it'd take an hour, don't.

## How to add a new one

1. Copy [`_template.md`](./_template.md) to a new file: `00NN-short-kebab-title.md` (next number, descriptive title).
2. Fill in the sections.
3. Add a row to the index below.
4. Set `Status` to **Proposed** while you're discussing it; flip to **Accepted** once locked in.

## Index

| #    | Title                                       | Status   |
|------|---------------------------------------------|----------|
| 0001 | [Backend stack](./0001-backend-stack.md)                              | Proposed |
| 0002 | [Data storage](./0002-data-storage.md)                                | Proposed |
| 0003 | [Tech stack and repo structure](./0003-tech-stack-and-repo-structure.md) | Accepted |
