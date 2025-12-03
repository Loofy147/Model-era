# Model-Era: A Hybrid Neuro-Symbolic Agent

This repository contains the implementation of a sophisticated autonomous agent designed for software engineering tasks. It integrates Neuro-Symbolic Logic, Agentic Self-Correction, Git Safety, and Hybrid Cost-Optimization to provide a powerful and efficient tool for developers.

## System Architecture

The agent's intelligence is distributed across a "model roster" that balances performance and cost:

*   **The Brain (Architect):** `gpt-4o` (or `claude-3-5-sonnet`) handles high-level planning, strategic thinking, and final security audits.
*   **The Hands (Coder):** `ollama/qwen2.5-coder` (or a fallback like `gpt-4o-mini`) is the specialist responsible for writing and debugging code.
*   **The Eyes (Clerk):** `ollama/llama3.2` is a fast, efficient model used for summarization, repository mapping, and other text-processing tasks.

This hybrid approach allows the system to use the most powerful models for critical thinking while offloading the bulk of the work to cheaper, specialized, or locally-run models, resulting in significant cost savings.

## Prerequisites

### 1. Install Python Libraries

Ensure you have the necessary Python packages installed:

```bash
pip install openai litellm pyyaml requests
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

### The Agentic Flow

When you run the command, the agent executes the following "Deep Logic Flow":

1.  **Safety First:** A new Git branch is created to sandbox the operation, ensuring your main branch remains clean.
2.  **Memory Retrieval:** The agent searches its long-term memory (`agent_memory.json`) for experiences from similar, past tasks. These experiences (both successes and failures) are used to provide context to the AI models, helping them avoid past mistakes and reuse successful strategies.
3.  **Mapping:** The `RepoCartographer` scans the codebase to create a contextual map.
4.  **Planning Loop (Architect & Validator):** The high-level task, along with the retrieved memories, is sent to the Architect model (`gpt-4o`) to create a detailed, strategic execution plan. This plan is then reviewed by a Validator persona (using the efficient `llama3.2` model). If the plan is flawed, it's sent back to the Architect for revision. This loop ensures only a high-quality plan proceeds.
4.  **Test-Driven Development:** Once the plan is approved, it is sent to the Coder model to generate a failing test (`repro_test.py`) that validates the final objective.
5.  **Reflexion Loop (Code & Fix):**
    *   The Coder writes an initial solution.
    *   The test is executed.
    *   If the test fails, the error is fed back to the Coder, which attempts to fix its own code. This loop continues until the test passes or a maximum number of retries is reached.
6.  **Security Audit:** Once the code passes the test, it is sent back to the Architect for a final security and style review.
7.  **Transplant & Commit:** If the audit is clean, the final, verified code from the `solution.py` in the workspace is copied to the target file (`src/database.py`), and the changes are committed to the new branch.
8.  **Cleanup:** If the process fails at any point, the sandbox branch is deleted, leaving your repository untouched.
