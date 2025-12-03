
import os
import json
import shutil
import subprocess
import time
from pathlib import Path

def run_benchmark():
    tasks_file = Path("benchmark/tasks.json")
    with open(tasks_file, 'r') as f:
        tasks = json.load(f)

    results = []
    for task in tasks:
        print(f"--- Running Benchmark Task: {task['id']} ---")

        # Prepare a clean environment
        target_file = Path(task['target_file'])
        backup_file = target_file.with_suffix(".bak")
        shutil.copy(target_file, backup_file)

        start_time = time.time()

        # Run the agent
        agent_process = subprocess.run(
            ["python", "main_hybrid.py", str(target_file), task['instruction']],
            capture_output=True, text=True
        )

        end_time = time.time()
        duration = end_time - start_time

        # Run the validation test
        validation_process = subprocess.run(
            ["python", task['validation_test']],
            capture_output=True, text=True
        )

        success = validation_process.returncode == 0

        results.append({
            "id": task['id'],
            "success": success,
            "duration": duration,
            "agent_stdout": agent_process.stdout,
            "agent_stderr": agent_process.stderr,
            "validation_stdout": validation_process.stdout,
            "validation_stderr": validation_process.stderr,
        })

        # Restore the original file
        shutil.move(backup_file, target_file)

    print("\n--- Benchmark Results ---")
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"- Task: {result['id']} | Status: {status} | Duration: {result['duration']:.2f}s")

if __name__ == "__main__":
    run_benchmark()
