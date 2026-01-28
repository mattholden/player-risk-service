#!/usr/bin/env python3
"""
Script to visualize token usage across the agent pipeline.

Plots cumulative token usage (completion, reasoning, prompt, and total tokens)
across all 5 agents in the pipeline, with vertical lines separating agent boundaries.
"""

import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


# Agent order in the pipeline
AGENT_ORDER = [
    "research_agent_1",
    "analyst_agent_1", 
    "research_agent_2",
    "analyst_agent_2",
    "shark_agent"
]

# Token types to plot
TOKEN_TYPES = ["completion_tokens", "reasoning_tokens", "prompt_tokens", "total_tokens"]

# Colors for each token type
COLORS = {
    "completion_tokens": "#2ecc71",  # Green
    "reasoning_tokens": "#9b59b6",   # Purple
    "prompt_tokens": "#3498db",      # Blue
    "total_tokens": "#e74c3c",       # Red
}

# Display names for legend
DISPLAY_NAMES = {
    "completion_tokens": "Completion Tokens",
    "reasoning_tokens": "Reasoning Tokens",
    "prompt_tokens": "Prompt Tokens",
    "total_tokens": "Total Tokens",
}


def load_token_data(json_path: str) -> dict:
    """Load token tracking data from JSON file."""
    with open(json_path, "r") as f:
        return json.load(f)


def compute_cumulative_data(data: dict) -> tuple[list[int], dict[str, list[int]], list[int], list[str]]:
    """
    Compute cumulative token counts across all agents.
    
    Returns:
        x_values: List of step indices (0, 1, 2, ...)
        cumulative_tokens: Dict mapping token type to cumulative values
        agent_boundaries: List of x-values where new agents start
        agent_labels: List of agent names for labeling boundaries
    """
    cumulative_tokens = {token_type: [] for token_type in TOKEN_TYPES}
    agent_boundaries = []
    agent_labels = []
    
    # Running totals for each token type
    running_totals = {token_type: 0 for token_type in TOKEN_TYPES}
    
    step_index = 0
    
    for agent_name in AGENT_ORDER:
        if agent_name not in data:
            print(f"Warning: Agent '{agent_name}' not found in data, skipping...")
            continue
            
        agent_data = data[agent_name]
        
        # Record boundary at start of each agent (except the first)
        if step_index > 0:
            agent_boundaries.append(step_index)
            agent_labels.append(agent_name)
        else:
            agent_labels.append(agent_name)
        
        # Get the token arrays for this agent
        # These are already cumulative within the agent, so we need the deltas
        for i, _ in enumerate(agent_data.get("total_tokens", [])):
            for token_type in TOKEN_TYPES:
                agent_tokens = agent_data.get(token_type, [])
                if i < len(agent_tokens):
                    # Get the value at this step
                    current_value = agent_tokens[i]
                    # Get previous value (0 if first step)
                    prev_value = agent_tokens[i - 1] if i > 0 else 0
                    # Add the delta to running total
                    delta = current_value - prev_value
                    running_totals[token_type] += delta
                    
                cumulative_tokens[token_type].append(running_totals[token_type])
            
            step_index += 1
    
    x_values = list(range(len(cumulative_tokens["total_tokens"])))
    
    return x_values, cumulative_tokens, agent_boundaries, agent_labels


def format_thousands(x, pos):
    """Format axis labels with K suffix for thousands."""
    if x >= 1000:
        return f'{x/1000:.0f}K'
    return f'{x:.0f}'


def plot_token_usage(
    x_values: list[int],
    cumulative_tokens: dict[str, list[int]],
    agent_boundaries: list[int],
    agent_labels: list[str],
    output_path: str = None,
    title: str = "Cumulative Token Usage Across Pipeline"
):
    """
    Create the token usage visualization.
    
    Args:
        x_values: Step indices
        cumulative_tokens: Dict of token type to cumulative values
        agent_boundaries: X-values where agents change
        agent_labels: Names of agents for boundary labels
        output_path: Optional path to save the figure
        title: Plot title
    """
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Plot each token type
    for token_type in TOKEN_TYPES:
        ax.plot(
            x_values,
            cumulative_tokens[token_type],
            label=DISPLAY_NAMES[token_type],
            color=COLORS[token_type],
            linewidth=2,
            marker='o',
            markersize=4,
            alpha=0.8
        )
    
    # Add vertical lines at agent boundaries
    boundary_colors = ['#7f8c8d', '#95a5a6', '#bdc3c7', '#ecf0f1']
    for i, boundary in enumerate(agent_boundaries):
        ax.axvline(
            x=boundary,
            color='#2c3e50',
            linestyle='--',
            linewidth=1.5,
            alpha=0.7
        )
        # Add agent label at the top
        ax.text(
            boundary,
            ax.get_ylim()[1] * 0.98,
            f' {agent_labels[i + 1]}',
            rotation=90,
            verticalalignment='top',
            fontsize=9,
            color='#2c3e50',
            alpha=0.8
        )
    
    # Add first agent label
    if agent_labels:
        ax.text(
            0,
            ax.get_ylim()[1] * 0.98,
            f' {agent_labels[0]}',
            rotation=90,
            verticalalignment='top',
            fontsize=9,
            color='#2c3e50',
            alpha=0.8
        )
    
    # Styling
    ax.set_xlabel('Tool Call Step', fontsize=12)
    ax.set_ylabel('Cumulative Tokens', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # Format y-axis with K suffix
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_thousands))
    
    # Grid
    ax.grid(True, alpha=0.3, linestyle='-')
    ax.set_axisbelow(True)
    
    # Legend
    ax.legend(loc='upper left', fontsize=10)
    
    # Tight layout
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {output_path}")
    
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Visualize token usage across the agent pipeline"
    )
    parser.add_argument(
        "json_file",
        nargs="?",
        default="token_tracking.json",
        help="Path to the token tracking JSON file (default: token_tracking.json)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path for the plot image (e.g., token_usage.png)"
    )
    parser.add_argument(
        "-t", "--title",
        default="Cumulative Token Usage Across Pipeline",
        help="Title for the plot"
    )
    
    args = parser.parse_args()
    
    # Resolve path relative to project root if needed
    json_path = Path(args.json_file)
    if not json_path.is_absolute():
        # Try relative to current directory first
        if not json_path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent
            json_path = project_root / args.json_file
    
    if not json_path.exists():
        print(f"Error: Could not find token tracking file at {json_path}")
        return 1
    
    print(f"Loading token data from: {json_path}")
    data = load_token_data(str(json_path))
    
    print(f"Found {len(data)} agents in data")
    for agent_name in AGENT_ORDER:
        if agent_name in data:
            steps = len(data[agent_name].get("total_tokens", []))
            print(f"  - {agent_name}: {steps} steps")
    
    # Compute cumulative data
    x_values, cumulative_tokens, agent_boundaries, agent_labels = compute_cumulative_data(data)
    
    print(f"\nTotal steps across all agents: {len(x_values)}")
    print(f"Agent boundaries at steps: {agent_boundaries}")
    
    # Create the plot
    plot_token_usage(
        x_values,
        cumulative_tokens,
        agent_boundaries,
        agent_labels,
        output_path=args.output,
        title=args.title
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
