#!/usr/bin/env python3
"""
Convert Chromium DOM API /layout response to data_format ui_tree.json format.

Reads JSON from stdin, writes converted ui_tree.json to stdout.

Usage:
    curl http://localhost:8122/layout | python layout_to_ui_tree.py > ui_tree.json
    cat layout.json | python layout_to_ui_tree.py > ui_tree.json
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone

# Track unmapped roles for debugging
_unmapped_roles = Counter()


# Role mapping from Chrome accessibility roles to data_format roles
# Chrome uses various naming conventions (camelCase, PascalCase, lowercase)
ROLE_MAP = {
    # Generic/container elements (very common)
    "generic": "panel",
    "none": "panel",
    "presentation": "panel",
    "group": "panel",
    "GenericContainer": "panel",
    "Group": "panel",

    # Document structure
    "RootWebArea": "window",
    "rootWebArea": "window",
    "WebArea": "panel",
    "webArea": "panel",
    "Document": "panel",
    "document": "panel",
    "Article": "panel",
    "article": "panel",
    "Section": "panel",
    "section": "panel",
    "Region": "panel",
    "region": "panel",
    "Main": "panel",
    "main": "panel",
    "Header": "panel",
    "header": "panel",
    "Footer": "panel",
    "footer": "panel",
    "Navigation": "panel",
    "navigation": "panel",
    "Complementary": "panel",
    "complementary": "panel",
    "Banner": "panel",
    "banner": "panel",
    "ContentInfo": "panel",
    "contentinfo": "panel",
    "Form": "panel",
    "form": "panel",
    "Search": "panel",
    "search": "panel",
    "Blockquote": "panel",
    "blockquote": "panel",
    "Figure": "panel",
    "figure": "panel",
    "FigureCaption": "label",
    "figcaption": "label",

    # Interactive elements
    "button": "button",
    "Button": "button",
    "link": "link",
    "Link": "link",
    "TextField": "textfield",
    "textField": "textfield",
    "textbox": "textfield",
    "TextBox": "textfield",
    "SearchBox": "textfield",
    "searchbox": "textfield",
    "SpinButton": "textfield",
    "spinbutton": "textfield",
    "TextArea": "textarea",
    "textarea": "textarea",
    "ComboBox": "combobox",
    "combobox": "combobox",
    "ComboBoxGrouping": "combobox",
    "ComboBoxMenuButton": "combobox",
    "ListBox": "listbox",
    "listbox": "listbox",
    "ListBoxOption": "listitem",
    "option": "listitem",
    "CheckBox": "checkbox",
    "checkbox": "checkbox",
    "RadioButton": "radiobutton",
    "radio": "radiobutton",
    "Switch": "checkbox",
    "switch": "checkbox",
    "Slider": "slider",
    "slider": "slider",
    "ScrollBar": "scrollbar",
    "scrollbar": "scrollbar",
    "ProgressIndicator": "progressbar",
    "progressbar": "progressbar",
    "Meter": "progressbar",
    "meter": "progressbar",

    # Menu elements
    "Menu": "menu",
    "menu": "menu",
    "MenuBar": "menubar",
    "menubar": "menubar",
    "MenuItem": "menuitem",
    "menuitem": "menuitem",
    "MenuItemCheckBox": "menuitem",
    "menuitemcheckbox": "menuitem",
    "MenuItemRadio": "menuitem",
    "menuitemradio": "menuitem",
    "MenuButton": "button",
    "MenuListPopup": "menu",

    # List elements
    "List": "listbox",
    "list": "listbox",
    "ListItem": "listitem",
    "listitem": "listitem",
    "DescriptionList": "listbox",
    "DescriptionListTerm": "listitem",
    "DescriptionListDetail": "listitem",
    "term": "listitem",
    "definition": "listitem",

    # Table elements
    "Table": "table",
    "table": "table",
    "Grid": "table",
    "grid": "table",
    "TreeGrid": "table",
    "treegrid": "table",
    "Row": "listitem",
    "row": "listitem",
    "RowGroup": "panel",
    "rowgroup": "panel",
    "Cell": "tablecell",
    "cell": "tablecell",
    "GridCell": "tablecell",
    "gridcell": "tablecell",
    "ColumnHeader": "tablecell",
    "columnheader": "tablecell",
    "RowHeader": "tablecell",
    "rowheader": "tablecell",

    # Tree elements
    "Tree": "treeview",
    "tree": "treeview",
    "TreeItem": "treeitem",
    "treeitem": "treeitem",

    # Tab elements
    "TabList": "panel",
    "tablist": "panel",
    "Tab": "tab",
    "tab": "tab",
    "TabPanel": "tabpanel",
    "tabpanel": "tabpanel",

    # Dialog elements
    "Dialog": "dialog",
    "dialog": "dialog",
    "AlertDialog": "dialog",
    "alertdialog": "dialog",
    "Alert": "dialog",
    "alert": "dialog",

    # Text elements
    "StaticText": "label",
    "staticText": "label",
    "InlineTextBox": "label",
    "inlineTextBox": "label",
    "Heading": "label",
    "heading": "label",
    "Paragraph": "label",
    "paragraph": "label",
    "LabelText": "label",
    "labelText": "label",
    "Legend": "label",
    "legend": "label",
    "Caption": "label",
    "caption": "label",
    "text": "label",

    # Media elements
    "Image": "image",
    "image": "image",
    "Img": "image",
    "img": "image",
    "Video": "panel",
    "video": "panel",
    "Audio": "panel",
    "audio": "panel",
    "Canvas": "image",
    "canvas": "image",
    "SVGRoot": "image",
    "svgRoot": "image",
    "graphics-document": "image",
    "graphics-object": "image",
    "graphics-symbol": "image",

    # Other elements
    "Toolbar": "toolbar",
    "toolbar": "toolbar",
    "Status": "statusbar",
    "status": "statusbar",
    "Tooltip": "tooltip",
    "tooltip": "tooltip",
    "Separator": "separator",
    "separator": "separator",
    "Splitter": "separator",
    "splitter": "separator",
    "Application": "panel",
    "application": "panel",
    "Iframe": "panel",
    "iframe": "panel",
    "IframePresentational": "panel",
    "EmbeddedObject": "panel",
    "PluginObject": "panel",
    "Presentation": "panel",
    "Math": "panel",
    "Note": "panel",
    "Log": "panel",
    "Marquee": "panel",
    "Timer": "label",
    "Definition": "label",
    "Term": "label",
    "Time": "label",
    "Abbr": "label",
    "Code": "label",
    "Pre": "panel",
    "Emphasis": "label",
    "Strong": "label",
    "Subscript": "label",
    "Superscript": "label",
    "Insertion": "label",
    "Deletion": "label",
    "Mark": "label",
    "LineBreak": "separator",
    "WordBreak": "separator",
    "Ruby": "label",
    "RubyAnnotation": "label",
}


def get_ax_value(obj):
    """Extract the value from an AXValue object."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("value")
    return obj


def map_role(ax_role):
    """Map Chrome accessibility role to data_format role."""
    if ax_role is None:
        return "unknown"
    role_str = str(ax_role)

    # Try exact match first
    if role_str in ROLE_MAP:
        return ROLE_MAP[role_str]

    # Try lowercase
    role_lower = role_str.lower()
    if role_lower in ROLE_MAP:
        return ROLE_MAP[role_lower]

    # Try common transformations
    # "FooBar" -> "foobar", "fooBar" -> "foobar"
    for key, value in ROLE_MAP.items():
        if key.lower() == role_lower:
            return value

    # Default: use the role as-is if it looks like a valid data_format role
    valid_roles = {
        "desktop", "window", "dialog", "panel", "toolbar", "menubar", "menu",
        "menuitem", "button", "checkbox", "radiobutton", "textfield", "textarea",
        "combobox", "listbox", "listitem", "tab", "tabpanel", "treeview", "treeitem",
        "table", "tablecell", "scrollbar", "slider", "progressbar", "label", "link",
        "image", "icon", "separator", "tooltip", "statusbar", "taskbar",
    }
    if role_lower in valid_roles:
        return role_lower

    # Track unmapped role for debugging
    _unmapped_roles[role_str] += 1
    return "unknown"


def get_states(node):
    """Extract states from accessibility node properties."""
    states = []
    properties = node.get("properties", [])

    state_map = {
        "focused": "focused",
        "selected": "selected",
        "checked": "checked",
        "disabled": "disabled",
        "expanded": "expanded",
        "collapsed": "collapsed",
        "hidden": "hidden",
        "editable": "editable",
        "readonly": "readonly",
        "pressed": "pressed",
        "busy": "active",
        "modal": "active",
    }

    for prop in properties:
        name = prop.get("name", "")
        value = get_ax_value(prop.get("value"))

        if name in state_map and value is True:
            states.append(state_map[name])
        elif name == "checked" and value == "true":
            states.append("checked")
        elif name == "expanded" and value is True:
            states.append("expanded")
        elif name == "expanded" and value is False:
            states.append("collapsed")

    # Check if node is ignored (hidden)
    if node.get("ignored"):
        if "hidden" not in states:
            states.append("hidden")

    return states if states else None


def build_tree(nodes):
    """Convert flat node list with childIds to hierarchical tree."""
    if not nodes:
        return None

    # Build lookup by nodeId
    node_map = {}
    for node in nodes:
        node_id = node.get("nodeId")
        if node_id:
            node_map[node_id] = node

    # Track which nodes are children (to find root)
    child_ids = set()
    for node in nodes:
        for child_id in node.get("childIds", []):
            child_ids.add(child_id)

    # Find root node (not a child of any other node)
    root_node = None
    for node in nodes:
        node_id = node.get("nodeId")
        if node_id and node_id not in child_ids:
            root_node = node
            break

    if root_node is None and nodes:
        # Fallback to first node
        root_node = nodes[0]

    if root_node is None:
        return None

    # Counter for generating sequential IDs
    id_counter = [0]

    def convert_node(ax_node):
        """Convert a single accessibility node to ui_tree format."""
        node_id = f"node_{id_counter[0]}"
        id_counter[0] += 1

        role = map_role(get_ax_value(ax_node.get("role")))
        name = get_ax_value(ax_node.get("name")) or ""

        # Get bounds
        bounds = ax_node.get("bounds")
        if bounds:
            ui_bounds = {
                "x": int(bounds.get("x", 0)),
                "y": int(bounds.get("y", 0)),
                "width": int(bounds.get("width", 0)),
                "height": int(bounds.get("height", 0)),
            }
        else:
            ui_bounds = {"x": 0, "y": 0, "width": 0, "height": 0}

        # Build the node
        ui_node = {
            "id": node_id,
            "role": role,
            "name": name,
            "bounds": ui_bounds,
        }

        # Add states if present
        states = get_states(ax_node)
        if states:
            ui_node["states"] = states

        # Recursively convert children
        child_ids = ax_node.get("childIds", [])
        if child_ids:
            children = []
            for child_id in child_ids:
                child_node = node_map.get(child_id)
                if child_node:
                    # Skip ignored nodes but include their children
                    if child_node.get("ignored"):
                        # Get grandchildren
                        for grandchild_id in child_node.get("childIds", []):
                            grandchild = node_map.get(grandchild_id)
                            if grandchild:
                                children.append(convert_node(grandchild))
                    else:
                        children.append(convert_node(child_node))
            if children:
                ui_node["children"] = children

        return ui_node

    return convert_node(root_node)


def convert_layout_to_ui_tree(layout_response):
    """Convert /layout response to ui_tree.json format."""
    # Get timestamp
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Default screen size
    screen = {"width": 1920, "height": 1080}

    # Process first tab (or could process all)
    tabs = layout_response.get("tabs", [])
    if not tabs:
        return {
            "timestamp": timestamp,
            "screen": screen,
            "root": {
                "id": "node_0",
                "role": "desktop",
                "name": "",
                "bounds": {"x": 0, "y": 0, "width": screen["width"], "height": screen["height"]},
                "children": [],
            },
        }

    tab = tabs[0]
    layout = tab.get("layout", {})
    nodes = layout.get("nodes", [])
    viewport = layout.get("viewport", {})

    # Get screen size from viewport
    if viewport:
        visual = viewport.get("visualViewport", {})
        if visual:
            screen["width"] = int(visual.get("width", 1920))
            screen["height"] = int(visual.get("height", 1080))

    # Build hierarchical tree from flat nodes
    root_content = build_tree(nodes)

    # Wrap in desktop root
    root = {
        "id": "node_0",
        "role": "desktop",
        "name": "",
        "bounds": {"x": 0, "y": 0, "width": screen["width"], "height": screen["height"]},
    }

    if root_content:
        # Renumber IDs since we added desktop root
        def renumber_ids(node, start=1):
            node["id"] = f"node_{start}"
            next_id = start + 1
            for child in node.get("children", []):
                next_id = renumber_ids(child, next_id)
            return next_id

        renumber_ids(root_content, 1)
        root["children"] = [root_content]

    return {
        "timestamp": timestamp,
        "screen": screen,
        "root": root,
    }


def main():
    # Read JSON from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        return 1

    # Convert
    ui_tree = convert_layout_to_ui_tree(input_data)

    # Output to stdout
    json.dump(ui_tree, sys.stdout, indent=2)
    print()  # Trailing newline

    # Report unmapped roles to stderr
    if _unmapped_roles:
        print(f"Warning: {sum(_unmapped_roles.values())} nodes with unmapped roles:", file=sys.stderr)
        for role, count in _unmapped_roles.most_common(10):
            print(f"  {role}: {count}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
