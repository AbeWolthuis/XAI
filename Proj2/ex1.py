from anytree.importer import DictImporter
from anytree import search
import os
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

    starting_node_name = 'getCoffee'
else:
    # json_tree: the JSON object representing the goal tree
    # starting_node_name: the name of the node from which to start enumerating
    importer = DictImporter()
    tree = importer.import_(json_tree) #ignore



# Our final output: A list of lists of node names.
output = []





def get_traces(node):
    """
    Given an anytree node, return all possible execution traces (list of names)
    for the subtree rooted at that node.
    """
    # If it's an ACT node, it's a leaf. The only trace is the node itself.
    if node.type == "ACT":
        return [[node.name]]

    # If it's a SEQ or AND node, execute all children in sequence (treat them the same).
    elif node.type in ["SEQ", "AND"]:
        # We sort children by their 'sequence' attribute if present, else use 0
        sorted_children = sorted(node.children,
                                 key=lambda c: getattr(c, 'sequence', 0))
        # Start with an empty "prefix" for accumulating partial traces
        all_traces = [[]]  # Will hold lists of node-name sequences so far
        for child in sorted_children:
            child_traces = get_traces(child)
            new_accum = []
            # For each accumulated partial trace, extend it by each child trace
            for prefix_trace in all_traces:
                for ct in child_traces:
                    new_accum.append(prefix_trace + ct)
            all_traces = new_accum

        # Prepend the current node's name to each trace
        for trace in all_traces:
            trace.insert(0, node.name)
        return all_traces

    # If it's an OR node, we can choose exactly one of the children.
    elif node.type == "OR":
        final_traces = []
        for child in node.children:
            child_traces = get_traces(child)
            # For each child trace, prepend this OR node's name
            for ct in child_traces:
                ct.insert(0, node.name)
            final_traces.extend(child_traces)
        return final_traces

    # If a node somehow has an unexpected type, return empty or handle appropriately
    return []




# 2) Find the node in the tree with name == starting_node_name
start_node = search.find_by_attr(tree, value=starting_node_name, name="name")
output = get_traces(start_node)

# 3) Write checks for the output,
if LOCAL:
    expected_output = [['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOwnCard', 'gotoKitchen', 'getCoffeeKitchen'],
                    ['getCoffee', 'getKitchenCoffee', 'getStaffCard', 'getOthersCard', 'gotoKitchen', 'getCoffeeKitchen'],
                    ['getCoffee', 'getAnnOfficeCoffee', 'gotoAnnOffice', 'getPod', 'getCoffeeAnnOffice'],
                    ['getCoffee', 'getShopCoffee', 'gotoShop', 'payShop', 'getCoffeeShop']]

    assert isinstance(output, list)
    assert all(isinstance(trace, list) for trace in output)
    assert output == expected_output

print(output)
