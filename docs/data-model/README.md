# Onus — Data Model

Documentation for the Onus data model: core entities, their relationships, and how
they map to the AML/CTF compliance domain — clients, matters, customer due
diligence (CDD), screening results, risk assessments, and the audit log.

> **Status: placeholder.** The schema is managed with Alembic migrations in
> [`engine/alembic/`](../../engine/alembic). Entity definitions and ERDs will be
> added here as the model is built out.
>
> **Forward data model:** the tables for the not-yet-built regulated sections
> (Clients & Matters, Compliance Program, Reporting, Independent Evaluation) are
> specified, grounded in AUSTRAC guidance, under [`../specs/`](../specs/README.md).
