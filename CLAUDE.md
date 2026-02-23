# Transportation AI Operating System
## Consultant Productivity Accelerator (Bootstrapped MVP)

You are assisting in building a Transportation Engineering AI SaaS platform.

This is a bootstrapped startup built by a solo founder working ~2 hours per day.
The goal is rapid, disciplined execution — not overengineering.

---

#  PRIMARY OBJECTIVE

Build a Consultant Productivity Accelerator focused on:

• Signalized intersection TIA workflow
• Scenario comparison
• Deterministic HCM computation
• Auditability
• Auto-generated LOS tables
• Report draft generation

We are NOT building:
• Full DTA
• Reinforcement learning
• GPU simulation
• Multi-service distributed systems
• Overly abstract architecture

MVP focus only.

---

#  PRODUCT VISION

This platform will:

1. Store structured transportation objects (not spreadsheets)
2. Run deterministic HCM computations
3. Support scenario diff versioning
4. Provide AI-assisted workflow suggestions
5. Export professional reports
6. Maintain legal defensibility

Agents may suggest.
Math engines must compute deterministically.

---

# TECH STACK (LOCKED)

Backend:
• Python 3.12
• FastAPI
• PostgreSQL 16 + PostGIS 3.4
• SQLAlchemy 2.x
• Alembic
• Pydantic v2
• Pytest

Frontend:
• React (Vite)
• Mapbox GL JS

Deployment:
• Docker
• AWS (Lightsail or EC2 initially)

NO Kubernetes.
NO microservices.
Single repository only.

---

#  ARCHITECTURE PRINCIPLES

1. Deterministic engineering core
   - HCM engine must be pure Python.
   - No LLM calls inside computation.
   - Fully unit-tested.
   - Versioned.

2. Structured data first
   - All inputs and outputs must use Pydantic models.
   - No free-form JSON.
   - No loosely typed structures.

3. Scenario-first design
   - Every modification stored as structured diff.
   - Results tied to engine version + input hash.
   - Full audit trail.

4. AI agents are advisory
   - They generate suggestions only.
   - They must output structured JSON.
   - They never override deterministic math.

5. Minimalism
   - Prefer clarity over abstraction.
   - Avoid premature optimization.
   - Avoid unnecessary design patterns.

---

#  CORE MVP SCOPE

We are currently building:

Phase 1:
• Intersection schema
• Signalized HCM engine
• API endpoint to compute LOS
• Scenario diff engine

Phase 2:
• Volume cleanup AI agent
• Scenario suggestion agent
• QA consistency checker
• Report draft generator

Anything outside this scope should be deferred.

---

#  DATABASE DESIGN PRINCIPLES

Tables include:

• projects
• nodes
• approaches
• lane_groups
• volumes
• scenarios
• scenario_changes
• runs
• results_lane_group
• results_node

All primary keys:
UUID

Nodes must include:
geometry(Point, 4326)

All result runs must include:
• engine_version
• input_hash
• timestamp

---

#  HCM ENGINE RULES

• No approximations unless explicitly documented.
• Code must be readable and testable.
• Separate:
    - capacity
    - v/c ratio
    - delay
    - LOS
• Must support unit tests for:
    - v/c < 1
    - v/c = 1
    - v/c > 1

Never mix database logic into engine.

---

#  WHAT NOT TO DO

Do NOT:

• Introduce microservices
• Suggest Kubernetes
• Propose distributed event-driven architecture
• Build full DTA
• Suggest rewriting in another language
• Overcomplicate schema
• Add premature caching
• Introduce GraphQL
• Suggest enterprise-scale patterns

We are bootstrapping.

---

#  TESTING REQUIREMENTS

All deterministic modules must include:
• Pytest tests
• Edge case coverage
• Clear expected outputs

AI-generated code must be reviewed and simplified if needed.

---

#  AI USAGE GUIDELINES

When writing code:

• Keep functions small.
• Avoid deep inheritance.
• Prefer explicit over magic.
• Add docstrings.
• Include version identifiers.

When unsure:
Ask for clarification before expanding scope.

---

#  LONG-TERM VISION (NOT FOR NOW)

Future modules may include:

• Corridor analysis
• TDM modeling
• DTA-lite
• Compliance automation
• Institutional memory knowledge graph

But MVP stays intersection-focused.

---

#  CURRENT PRIORITY

Right now we are building:

Signalized Intersection HCM Engine + API Integration.

Focus only on that unless instructed otherwise.

---

# END OF CLAUDE INSTRUCTIONS
