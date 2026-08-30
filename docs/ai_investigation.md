# AI Investigation & Agentic Finance Controller (Phase 6)

## Overview
Phase 6 introduces an AI-powered agentic controller that investigates deterministic reconciliation failures. It operates strictly as a read-only analyst, following a rigid fact-finding workflow before leveraging Large Language Models (LLMs) to explain financial discrepancies.

## Core Principles
1. **Facts First**: The agent gathers hard evidence from the database using restricted, read-only tools.
2. **No Hallucinations**: LLMs do not make financial decisions; they only interpret facts.
3. **Read-Only**: The agent cannot move money, update ledgers, or modify database records.
4. **Isolated Ground Truth**: The agent has zero access to `ground_truth.csv`.
5. **Provider Agnostic**: The architecture supports multiple LLM providers (e.g., Gemini) and includes a `MockLLMProvider` for offline testing.

## Architecture

### Components
- **AgentInvestigationController**: State machine that manages the investigation lifecycle (`START` -> `LOAD_RECONCILIATION` -> `GATHER_EVIDENCE` -> `ANALYZE` -> `VALIDATE` -> `COMPLETE`/`ESCALATE`).
- **Router**: Selects the appropriate investigation strategy (tools, prompt context) based on the deterministic reason code (e.g., `FEE_DIFFERENCE`, `TIMING_MISMATCH`).
- **Tools**: Secure, parameterized read-only functions to query orders, payments, refunds, settlements, and bank transactions.
- **Provider**: Abstraction for LLM interactions.
- **Validator**: Ensures the AI's explanation aligns with the gathered facts. Escalate to human review if hallucinations or deviations are detected.

### Data Flow
1. API receives a request to investigate a `case_id`.
2. The Controller loads the Phase 4 deterministic reconciliation result.
3. The Router determines the investigation strategy based on the reason code.
4. The Agent gathers evidence using predefined read-only tools.
5. The LLM provider analyzes the evidence and outputs an explanation and recommendation.
6. The Validator cross-checks the LLM's output against the gathered evidence.
7. If validation passes, the investigation completes. If it fails, it is escalated for human review.

## API Endpoints
- `POST /api/investigations/{case_id}`: Trigger a new investigation.
- `GET /api/investigations/{case_id}`: Retrieve the results of an investigation.

## Usage (Local/Testing)
To run offline or in CI environments without external API calls, set `USE_MOCK_LLM=true` in your `.env` file.
