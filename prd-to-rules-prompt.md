You are an expert software architect and technical lead tasked with creating a comprehensive RULES.md file based on the Product Requirements Document (PRD.md) and features list (FEATURES.md), or the documents provided in the conversation.

Create a clear, structured RULES.md that establishes technical and general guidelines for AI assistance during the development process. These rules will ensure consistency, quality, and alignment with project requirements.

If any critical information is missing or unclear, ask specific questions before proceeding.

## SCOPE THE CHECKLIST TO THE PRODUCT TYPE

First classify the product: web app · mobile app · library/SDK · CLI · service/API · data pipeline · game.

Apply only the sections and checks that fit that type. For a library/SDK, skip infrastructure, scalability, regulatory, business-model, accessibility, responsive-design, state-management, and auth concerns -- instead probe: public API surface and consistency, semver/deprecation policy, peer-dependency ranges, bundle size, tree-shaking, types quality, the public/internal boundary, and mutation of caller-owned data. Every other product type has its own equivalents; work them out before applying the generic list below.

State which product type you classified and which checks you skipped. Skipping must be visible and auditable, never silent -- a generated "no SQL injection vectors identified" in a library that has no SQL manufactures false confidence.

Generate the RULES.md by:

1. TECHNOLOGY STACK DEFINITION:
   - Identify core technologies mentioned or implied in the PRD/features
   - Specify the latest stable versions for each technology
   - Define required libraries, frameworks, or tools

2. TECHNICAL PREFERENCES:
   - Naming conventions for files, components, variables, etc.
   - Code organization principles (folder structure, modularity)
   - Architectural patterns to follow
   - Standards for data handling, state management, and API interactions
   - Performance optimization strategies
   - Security practices and requirements

3. DEVELOPMENT STANDARDS:
   - Testing requirements and coverage expectations
   - Error handling and logging requirements
   - Accessibility standards
   - Responsive design requirements

4. IMPLEMENTATION PRIORITIES:
   - Core features vs. enhancements (MoSCoW)
   - Phased implementation approach
   - Quality thresholds that must be met

5. GENERAL GUIDELINES:
   - Rules for following requirements precisely
   - Expectations for code quality, readability, and maintainability
   - Standards for completeness (no TODOs or placeholders)
   - How to handle uncertainty or ambiguity

6. AGENT CONFIGURATION:
   - If the project uses an AI coding agent, recommend wiring RULES.md into its config so the rules stay in context: reference it from CLAUDE.md (Claude Code), AGENTS.md (Codex and others), or .cursor/rules/ (Cursor)

First, provide a brief overview of the project based on the PRD and features list. Then create the RULES.md content. Ensure the rules are specific enough to guide development but flexible enough to allow for creative problem-solving.
