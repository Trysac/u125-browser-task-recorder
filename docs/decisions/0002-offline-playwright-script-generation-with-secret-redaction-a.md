# Offline Playwright Script Generation with Secret Redaction and Safe Escaping

Status: accepted (generated, pending human review)

## Context

Browser automation tasks recorded via browser extensions or Chrome DevTools often leak typed credentials into exported files and test suites. Furthermore, direct string concatenation in codegen tools risks script injection when untrusted selectors or input strings contain quotes and special characters.

## Decision

Implement browser-task-recorder as a zero-runtime-dependency library that parses native and Chrome DevTools Recorder recordings offline. Emit Playwright Python scripts using strict repr() literal escaping and map secret input fields into sequentially numbered environment variables.

## Consequences

Generated scripts are clean, reproducible, and safe from credential leakage and injection. Playwright is only needed at runtime execution of the generated script, not during conversion.
