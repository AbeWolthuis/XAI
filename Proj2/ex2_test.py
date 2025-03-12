from anytree.importer import DictImporter
from anytree import search
import os
from anytree import Node, AnyNode, RenderTree
import json

LOCAL = True

# 1) Load the tree
def load_json_tree_locally(file_name="coffee.json"):
    """
    Loads the coffee.json file from the same directory
    and returns the JSON dictionary.
    """
    json_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

if LOCAL:
    # Should be path relative
    json_data = load_json_tree_locally("coffee.json")
    importer = DictImporter()
    tree = importer.import_(json_data)

    norm = {'type': 'P', 'actions': ['gotoKitchen']}  # Example norm prohibiting 'gotoKitchen'
else:
    # json_tree: the JSON object representing the goal tree
    # starting_node_name: the name of the node from which to start enumerating
    importer = DictImporter()
    tree = importer.import_(json_tree) #ignore

    print(f"Norm is: {norm}\n\n")

# 2) Annotate tree
def annotate_tree(node, norm):
    """Creates an exact copy of the node, preserving attributes if they are present, and adds the violation attribute."""
    violation = False
    
    if node.type == "ACT":
        if norm["type"] == "P" and node.name in norm["actions"]:
            violation = True
        elif norm["type"] == "O" and node.name not in norm["actions"]:
            violation = True
    
    # Create annotated node first
    node_attributes = {"name": node.name, "type": node.type, "violation": violation}
    
    for attr in ["pre", "post", "sequence", "link", "slink", "costs"]:
        value = getattr(node, attr, None)
        
        if value not in [None, [], ""]:
            # Check if an entry is formatted as an int (a digit without period) and if so, convert it to int
            if isinstance(value, int):
                value = int(value)
            if isinstance(value, list):
                # Convert floats ending in 0 to int
                value = [int(v) if isinstance(v, float) and v.is_integer() else v for v in value]
            node_attributes[attr] = value
    
    annotated_node = AnyNode(**node_attributes)
    
    child_violations = []
    
    for child in node.children:
        new_child = annotate_tree(child, norm)
        new_child.parent = annotated_node
        child_violations.append(new_child.violation)
    
    # If it's a SEQ node and any child has a violation, the node itself is a violation
    if node.type == "SEQ" and any(child_violations):
        annotated_node.violation = True
    
    # If it's an OR node, it should only be a violation if ALL its children are violations
    if node.type == "OR" and all(child_violations):
        annotated_node.violation = True
    
    return annotated_node


annotated_tree = annotate_tree(tree, norm)


# 3)  Quality checks
output = RenderTree(annotated_tree)
if LOCAL:
    # Assertion to check the structure and violations
    expected_tree_str = """AnyNode(name='getCoffee', type='OR', violation=False)
├── AnyNode(name='getKitchenCoffee', pre=['staffCardAvailable'], type='SEQ', violation=True)
│   ├── AnyNode(name='getStaffCard', sequence=1, type='OR', violation=False)
│   │   ├── AnyNode(costs=[0, 0, 0], link=['getCoffeeKitchen'], name='getOwnCard', post=['haveCard'], pre=['ownCard'], type='ACT', violation=False)
│   │   └── AnyNode(costs=[0, 0, 2], link=['getCoffeeKitchen'], name='getOthersCard', post=['haveCard'], pre=['colleagueAvailable'], type='ACT', violation=False)
│   ├── AnyNode(costs=[0, 0, 2], link=['getCoffeeKitchen'], name='gotoKitchen', post=['atKitchen'], sequence=2, type='ACT', violation=True)
│   └── AnyNode(costs=[5, 0, 1], name='getCoffeeKitchen', post=['haveCoffee'], pre=['haveCard', 'atKitchen'], sequence=3, slink=['getOwnCard', 'getOthersCard', 'gotoKitchen'], type='ACT', violation=False)
├── AnyNode(name='getAnnOfficeCoffee', pre=['AnnInOffice'], type='SEQ', violation=False)
│   ├── AnyNode(costs=[0, 0, 2], link=['getCoffeeAnnOffice'], name='gotoAnnOffice', post=['atAnnOffice'], pre=['AnnInOffice'], sequence=1, type='ACT', violation=False)
│   ├── AnyNode(costs=[0, 0, 1], link=['getCoffeeAnnOffice'], name='getPod', post=['havePod'], sequence=2, type='ACT', violation=False)
│   └── AnyNode(costs=[2, 0, 3], name='getCoffeeAnnOffice', post=['haveCoffee'], pre=['havePod', 'atAnnOffice'], sequence=3, slink=['gotoAnnOffice', 'getPod'], type='ACT', violation=False)
└── AnyNode(name='getShopCoffee', pre=['haveMoney'], type='SEQ', violation=False)
    ├── AnyNode(costs=[0, 0, 5], link=['getCoffeeShop'], name='gotoShop', post=['atShop'], sequence=1, type='ACT', violation=False)
    ├── AnyNode(costs=[0, 3, 1], link=['getCoffeeShop'], name='payShop', post=['paidShop'], pre=['haveMoney'], sequence=2, type='ACT', violation=False)
    └── AnyNode(costs=[0, 0, 3], name='getCoffeeShop', post=['haveCoffee'], pre=['atShop', 'paidShop'], sequence=3, slink=['gotoShop', 'payShop'], type='ACT', violation=False)"""
    
    # Convert the rendered tree to a string representation
    rendered_tree_str = "\n".join([f"{pre}{node}" for pre, _, node in RenderTree(annotated_tree)])
    
    if not rendered_tree_str == expected_tree_str:
        print('Trees not the same. \n')
        # Print which lines are not the same, on newlines, with one whitespace after the two lines.
        for l1, l2 in zip(rendered_tree_str.split('\n'), expected_tree_str.split('\n')):
            if l1 != l2:
                print(f'Result:  {l1}\nCorrect: {l2}\n')
        print("❌ Trees are NOT the same. \n")
    else:
        print("✅ Trees are the same. \n")

# 4) Render tree.
def render_tree_violations_only(tree):
    """Render the tree with violation attribute only."""
    return RenderTree(tree).by_attr(lambda n: f"{n.name} (Violation: {n.violation})")
if LOCAL:
    # print(output)
    pass
else:
    print(output)




