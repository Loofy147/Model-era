
import argparse
import os
from repo_cartographer import RepoCartographer
from flow_engineer import FlowEngineer

def main():
    """
    The main entry point for the Unified CLI.
    """
    parser = argparse.ArgumentParser(
        description="An agentic software engineer that maps a repository and executes a task."
    )
    parser.add_argument(
        "task",
        type=str,
        help="The software engineering task to be performed."
    )
    parser.add_argument(
        "--repo-path",
        type=str,
        default=".",
        help="The path to the repository to analyze."
    )
    parser.add_argument(
        "--map-file",
        type=str,
        default="repo_map.json",
        help="The file to save the repository map to."
    )
    args = parser.parse_args()

    # --- Phase 1: The Repo Cartographer ---
    print("--- Initiating Phase 1: Repository Mapping ---")
    cartographer = RepoCartographer(args.repo_path)
    cartographer.map_repo()
    cartographer.export_map(args.map_file)
    print("--- Phase 1 Complete: Repository Map Generated ---")

    # --- Phase 2: The Flow Engineer ---
    if not os.path.exists(args.map_file):
        print(f"Error: Repository map file '{args.map_file}' not found. Aborting.")
        return

    print("\n--- Initiating Phase 2: Logic Engineering Flow ---")
    engineer = FlowEngineer(args.map_file)
    engineer.execute_flow(args.task)
    print("--- Phase 2 Complete: Logic Engineering Flow Finished ---")

if __name__ == "__main__":
    main()
