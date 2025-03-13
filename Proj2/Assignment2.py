'''
this code is written such that it can only be ran on colab or directly in the PrairieLearn env, soz
'''


from anytree import AnyNode, RenderTree
def build_annotated_tree(data, norm, parent=None):
    # Extract keys (attributes) dynamically
    node_attributes = {k: v for k, v in data.items() if k != "children"}
    
    node_attributes["violation"] = False

    # Create a new node with all attributes
    node = AnyNode(parent=parent, **node_attributes)

    norm_type = norm.get("type")

    #actions only
    if node.type == "ACT": 
            if norm_type == "P":
                node.violation = node.name in norm['actions']
            elif norm_type == "O":
                node.violation = node.name not in norm['actions']

    # Recursively add children
    for child in data.get("children", []):
        build_annotated_tree(child, norm, parent=node)

    # any child with violation means this node is a violatoin
    if node.type in ["SEQ", "AND"]:
        node.violation = any(child.violation for child in getattr(node, 'children', []))
    
    # all children have to be with violation for this node to be a violation too
    if node.type == "OR":
        node.violation = all(child.violation for child in getattr(node, 'children', []))

    return node


root = build_annotated_tree(json_tree, norm)
output = RenderTree(root)