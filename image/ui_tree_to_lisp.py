#!/usr/bin/env python3
"""
Convert ui_tree.json to a compact, human-readable lisp-style representation.

Reads JSON from stdin, writes lisp-style text to stdout.

Usage:
    cat ui_tree.json | python ui_tree_to_lisp.py
    curl http://localhost:8122/layout | python layout_to_ui_tree.py | python ui_tree_to_lisp.py

Format Documentation:
=====================

The output is an S-expression tree where each node has the format:

    (role "name" [x,y wxh] [:state1 :state2 ...]
      <children>)

Components:
- role      : UI role (button, link, textfield, etc.) - unquoted symbol
- "name"    : Display text in quotes (omitted if empty)
- [x,y wxh] : Bounds as [x,y widthxheight] (omitted with --no-bounds)
- :states   : Colon-prefixed state keywords (omitted if none)
- children  : Nested child nodes (indented)

Examples:
---------

Single button:
    (button "Submit" [100,200 80x32] :focused)

Window with children:
    (window "My App" [0,0 1920x1080]
      (toolbar [0,0 1920x40]
        (button "File" [10,5 50x30])
        (button "Edit" [70,5 50x30]))
      (panel "Content" [0,40 1920x1040]
        (textfield "Search..." [10,10 200x30] :editable :focused)))

Compact mode (--compact):
    (window "My App" (toolbar (button "File")(button "Edit"))(panel "Content" (textfield "Search..." :editable)))

Options:
--------
--no-bounds     : Omit coordinate information
--no-states     : Omit state information
--compact       : Single-line output, no indentation
--no-empty      : Skip nodes with empty names and no children
--max-depth N   : Limit tree depth to N levels
--min-size N    : Skip nodes smaller than NxN pixels
"""

import argparse
import json
import sys


def escape_string(s):
    """Escape a string for lisp output."""
    if not s:
        return None
    # Escape backslashes and quotes
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    # Replace newlines and tabs
    s = s.replace("\n", "\\n").replace("\t", "\\t")
    return f'"{s}"'


def format_bounds(bounds):
    """Format bounds as [x,y wxh]."""
    if not bounds:
        return None
    x = bounds.get("x", 0)
    y = bounds.get("y", 0)
    w = bounds.get("width", 0)
    h = bounds.get("height", 0)
    return f"[{x},{y} {w}x{h}]"


def format_states(states):
    """Format states as :state1 :state2 ..."""
    if not states:
        return None
    return " ".join(f":{s}" for s in states)


def node_to_lisp(node, opts, depth=0):
    """Convert a UI tree node to lisp format."""
    if node is None:
        return None

    # Check depth limit
    if opts.max_depth is not None and depth > opts.max_depth:
        return None

    role = node.get("role", "unknown")
    name = node.get("name", "")
    bounds = node.get("bounds")
    states = node.get("states", [])
    children = node.get("children", [])

    # Check minimum size filter
    if opts.min_size and bounds:
        w = bounds.get("width", 0)
        h = bounds.get("height", 0)
        if w < opts.min_size and h < opts.min_size:
            return None

    # Skip empty nodes if requested
    if opts.no_empty and not name and not children:
        return None

    # Build node parts
    parts = [role]

    # Add name if present
    name_str = escape_string(name)
    if name_str:
        parts.append(name_str)

    # Add bounds unless disabled
    if not opts.no_bounds and bounds:
        bounds_str = format_bounds(bounds)
        if bounds_str:
            parts.append(bounds_str)

    # Add states unless disabled
    if not opts.no_states and states:
        states_str = format_states(states)
        if states_str:
            parts.append(states_str)

    # Convert children
    child_lisps = []
    for child in children:
        child_lisp = node_to_lisp(child, opts, depth + 1)
        if child_lisp:
            child_lisps.append(child_lisp)

    # Format output
    if opts.compact:
        # Single line, no spaces between children
        if child_lisps:
            children_str = "".join(child_lisps)
            return f"({' '.join(parts)}{children_str})"
        else:
            return f"({' '.join(parts)})"
    else:
        # Pretty printed with indentation
        indent = "  " * depth
        child_indent = "  " * (depth + 1)

        if child_lisps:
            # Multi-line with children
            header = f"({' '.join(parts)}"
            child_lines = []
            for child_lisp in child_lisps:
                # Indent each line of child
                child_lines.append(child_indent + child_lisp.replace("\n", "\n" + child_indent))
            return header + "\n" + "\n".join(child_lines) + ")"
        else:
            return f"({' '.join(parts)})"


def convert_ui_tree_to_lisp(ui_tree, opts):
    """Convert full ui_tree.json to lisp format."""
    lines = []

    # Add header comment with metadata
    if not opts.compact:
        timestamp = ui_tree.get("timestamp", "")
        screen = ui_tree.get("screen", {})
        if timestamp or screen:
            lines.append(f";; UI Tree")
            if timestamp:
                lines.append(f";; timestamp: {timestamp}")
            if screen:
                w = screen.get("width", 0)
                h = screen.get("height", 0)
                lines.append(f";; screen: {w}x{h}")
            lines.append("")

    # Convert root node
    root = ui_tree.get("root")
    if root:
        root_lisp = node_to_lisp(root, opts)
        if root_lisp:
            lines.append(root_lisp)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Convert ui_tree.json to lisp-style representation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[0],
    )
    parser.add_argument(
        "--no-bounds",
        action="store_true",
        help="Omit coordinate/bounds information",
    )
    parser.add_argument(
        "--no-states",
        action="store_true",
        help="Omit state information",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Single-line output without indentation",
    )
    parser.add_argument(
        "--no-empty",
        action="store_true",
        help="Skip nodes with empty names and no children",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum tree depth to output",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=None,
        help="Skip nodes smaller than NxN pixels",
    )

    args = parser.parse_args()

    # Read JSON from stdin
    try:
        ui_tree = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        return 1

    # Convert and output
    output = convert_ui_tree_to_lisp(ui_tree, args)
    print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
