# UI Tree Lisp Format

A compact, human-readable S-expression format for representing UI trees.

## Syntax

```
(role "name" [x,y wxh] :state1 :state2 ...
  <children>)
```

### Components

| Component | Required | Description |
|-----------|----------|-------------|
| `role` | Yes | UI role as unquoted symbol (button, link, panel, etc.) |
| `"name"` | No | Display text in double quotes (omitted if empty) |
| `[x,y wxh]` | No | Bounds: `[left,top widthxheight]` in pixels |
| `:state` | No | Colon-prefixed keywords for states |
| children | No | Nested nodes, indented on new lines |

### Roles

Standard roles: `desktop`, `window`, `dialog`, `panel`, `toolbar`, `menubar`, `menu`, `menuitem`, `button`, `checkbox`, `radiobutton`, `textfield`, `textarea`, `combobox`, `listbox`, `listitem`, `tab`, `tabpanel`, `treeview`, `treeitem`, `table`, `tablecell`, `scrollbar`, `slider`, `progressbar`, `label`, `link`, `image`, `icon`, `separator`, `tooltip`, `statusbar`, `unknown`

### States

Standard states: `:focused`, `:selected`, `:checked`, `:disabled`, `:expanded`, `:collapsed`, `:visible`, `:hidden`, `:editable`, `:readonly`, `:pressed`, `:active`

## Examples

### Simple Button
```lisp
(button "Submit" [100,200 80x32])
```

### Focused Text Field
```lisp
(textfield "Search..." [10,50 200x30] :focused :editable)
```

### Nested Structure
```lisp
(window "My Application" [0,0 1920x1080]
  (toolbar [0,0 1920x40]
    (button "File" [10,5 50x30])
    (button "Edit" [70,5 50x30])
    (button "View" [130,5 50x30]))
  (panel "Main Content" [0,40 1920x1000]
    (label "Welcome" [20,20 200x24])
    (textfield [20,50 400x30] :editable)
    (button "Submit" [20,90 100x32])))
```

### Complex Form
```lisp
(dialog "Login" [500,200 400x300]
  (label "Username" [20,20 100x20])
  (textfield [20,45 360x30] :editable :focused)
  (label "Password" [20,85 100x20])
  (textfield [20,110 360x30] :editable)
  (checkbox "Remember me" [20,150 150x20])
  (panel [20,200 360x50]
    (button "Cancel" [0,10 80x30])
    (button "Login" [280,10 80x30] :pressed)))
```

### Compact Form (single line)
```lisp
(window "App"(toolbar(button "File")(button "Edit"))(panel(textfield :editable)))
```

## Command Line Options

```
--no-bounds    Omit [x,y wxh] coordinates
--no-states    Omit :state keywords
--compact      Single-line output, no indentation
--no-empty     Skip nodes with empty names and no children
--max-depth N  Limit output to N levels deep
--min-size N   Skip nodes smaller than NxN pixels
```

## Usage Examples

```bash
# Full output with bounds and states
cat ui_tree.json | python ui_tree_to_lisp.py

# Semantic structure only (no coordinates)
cat ui_tree.json | python ui_tree_to_lisp.py --no-bounds

# Compact single-line
cat ui_tree.json | python ui_tree_to_lisp.py --compact

# First 3 levels only
cat ui_tree.json | python ui_tree_to_lisp.py --max-depth 3

# Skip tiny elements
cat ui_tree.json | python ui_tree_to_lisp.py --min-size 10

# Pipeline from API
curl -s http://localhost:8122/layout \
  | python layout_to_ui_tree.py \
  | python ui_tree_to_lisp.py --no-bounds
```

## Output Header

Pretty-printed output includes a comment header with metadata:

```lisp
;; UI Tree
;; timestamp: 2025-01-29T12:00:00Z
;; screen: 1920x1080

(desktop [0,0 1920x1080]
  ...)
```

## Parsing

The format is valid S-expression syntax and can be parsed with any lisp reader. For simple parsing:

1. `(` starts a node
2. First token is the role
3. Quoted string is the name
4. `[...]` is bounds
5. `:keyword` tokens are states
6. Nested `(...)` are children
7. `)` ends the node

## Design Rationale

- **Compact**: ~60-70% smaller than JSON for typical UI trees
- **Readable**: Hierarchical indentation shows structure at a glance
- **Greppable**: Easy to search for `(button "Submit"` or `:focused`
- **Diffable**: Line-per-node makes version control diffs meaningful
- **Flexible**: Options to include/exclude bounds, states as needed
