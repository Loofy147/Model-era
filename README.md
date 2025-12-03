# Model-Era: A Hybrid Neuro-Symbolic Agent

This repository contains the implementation of a sophisticated autonomous agent designed for software engineering tasks. It integrates Neuro-Symbolic Logic, Agentic Self-Correction, Git Safety, and Hybrid Cost-Optimization to provide a powerful and efficient tool for developers.

## System Architecture

The system is designed as a **multi-agent collaboration framework**, orchestrated by a `TeamManager`. Each agent is a specialized persona responsible for a specific phase of the software development lifecycle. They collaborate by reading from and writing to a `SharedContext` object, which acts as a central scratchpad for the task.

### The Agent Team

*   **Architect:** (Model: `gpt-4o`) The strategic leader. It analyzes the user's request, codebase map, and past experiences to create a detailed, multi-step YAML plan.
*   **Validator:** (Model: `ollama/llama3.2`) The gatekeeper. It reviews the Architect's plan for logical flaws or vagueness. If the plan is weak, it provides a critique and sends it back for revision.
*   **QA Engineer:** (Model: `ollama/qwen2.5-coder`) The test writer. Following the approved plan, it writes a Python test script that will fail until the required changes are correctly implemented.
*   **Coder:** (Model: `ollama/qwen2.5-coder`) The implementer. It writes the source code to satisfy the test harness and fulfill the plan's requirements.
*   **Debugger:** (Model: `ollama/qwen2.5-coder`) The problem solver. If the Coder's solution fails the test, the Debugger is activated. It analyzes the error and attempts to rewrite the code to fix the issue.
*   **Auditor:** (Model: `gpt-4o`) The final reviewer. Once the code passes all tests, the Auditor performs a final check for security vulnerabilities, style issues, and adherence to the original plan.

### The Orchestrator: `TeamManager`

The `TeamManager` coordinates the entire workflow. It initializes the `SharedContext` and manages a state machine that determines which agent's turn it is to act. It passes the context to each agent and transitions the state based on the outcome of their work, orchestrating the seamless collaboration of the entire team.

## Prerequisites

### 1. Install Python Libraries

Ensure you have the necessary Python packages installed:

```bash
pip install openai litellm pyyaml requests flake8
```

### 2. Set Up Open Source Engine (Optional but Recommended)

For maximum cost-efficiency, you can run the Coder and Clerk models locally using Ollama.

1.  **Install Ollama:** Follow the instructions at [https://ollama.ai/](https://ollama.ai/).
2.  **Pull the Models:**
    ```bash
    ollama pull qwen2.5-coder:14b  # High-fidelity coding model
    ollama pull llama3.2           # Fast text processing model
    ```
3.  **Start the Server:**
    ```bash
    ollama serve
    ```

If Ollama is not available, the system will automatically fall back to a cloud-based model like `gpt-4o-mini`.

### 3. Export API Keys

The agent requires an OpenAI API key for the Architect model.

```bash
export OPENAI_API_KEY="sk-..."
```

## How to Use the Agent

The agent is executed via the `main_hybrid.py` script. It takes two arguments: the target file to be modified and a natural language instruction describing the task.

### Example

To add a database connection pool with a retry mechanism to a file named `src/database.py`, you would run:

```bash
python main_hybrid.py src/database.py "Add a connection pool with a retry mechanism for timeout errors"
```

## Benchmarking

To measure the agent's performance and track its improvement over time, a benchmarking framework is included.

### How to Run the Benchmark

To run the full suite of benchmark tasks, execute the following command:

```bash
python benchmark_runner.py
```

The runner will execute each task defined in `benchmark/tasks.json`, run a separate validation test to confirm the correctness of the agent's solution, and print a summary report of the results.

### The Agentic Flow

When you run the command, the agent executes the following "Deep Logic Flow":

1.  **Safety First:** A new Git branch is created to sandbox the operation, ensuring your main branch remains clean.
2.  **Memory Retrieval:** The agent searches its long-term memory (`agent_memory.json`) for experiences from similar, past tasks. These experiences (both successes and failures) are used to provide context to the AI models, helping them avoid past mistakes and reuse successful strategies.
3.  **Mapping:** The `RepoCartographer` scans the codebase to create a contextual map.
4.  **Planning Loop (Architect & Validator):** The high-level task, along with the retrieved memories, is sent to the Architect model (`gpt-4o`) to create a detailed, strategic execution plan. This plan is then reviewed by a Validator persona (using the efficient `llama3.2` model). If the plan is flawed, it's sent back to the Architect for revision. This loop ensures only a high-quality plan proceeds.
5.  **Test-Driven Development:** Once the plan is approved, it is sent to the Coder model to generate a failing test (`repro_test.py`) that validates the final objective.
6.  **Reflexion Loop (Code & Fix):**
    *   The Coder writes an initial solution.
    *   The test is executed.
    *   If the test fails, the error is fed back to the Coder, which attempts to fix its own code. This loop continues until the test passes or a maximum number of retries is reached.
7.  **Automated Refactoring:** After the code passes the tests, it is automatically linted using `flake8`. If any style issues are found, a `REFACTOR_AGENT` is invoked to clean up the code. The tests are re-run to ensure the refactoring did not break functionality.
8.  **Security Audit:** Once the code is functional and clean, it is sent to the Auditor for a final security and style review.
9.  **Transplant & Commit:** If the audit is clean, the final, verified code is copied to the target file, and the changes are committed.
10. **Cleanup:** If the process fails, the sandbox branch is deleted, leaving the repository untouched.
