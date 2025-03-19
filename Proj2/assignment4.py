from anytree import AnyNode, PreOrderIter
import numpy as np
import random

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
    
def execution_trace(node, beliefs, goal, trace=None):
    if trace is None:
        trace = []  # Start with an empty execution trace

    if getattr(node, "violation", False):
        return []  # If the node is invalid, return no trace

    # If we reach an action node, check if it achieves the goal
    if node.type == "ACT":
        if hasattr(node, "post") and goal == beliefs:
            return [trace + [node]]
        elif not hasattr(node, "pre") or all(p in beliefs for p in node.pre):
            new_beliefs = beliefs.union(set(getattr(node, "post", [])))  # Update beliefs
            return [trace + [node]]  # Store only trace (beliefs update dynamically)
        else:
            return []  # Preconditions not met, cannot execute

    # Handle OR nodes: **Explore all child nodes**
    if node.type == "OR":
        total_traces = []
        for child in node.children:
            child_traces = execution_trace(child, beliefs.copy(), goal, trace + [node])
            total_traces.extend(child_traces)  # Collect all valid traces
        return total_traces

    # Handle SEQ nodes: **Execute children in order & update beliefs**
    if node.type in ["SEQ", "AND"]:
        current_trace = trace + [node]  # Include the SEQ node itself in the trace
        current_beliefs = beliefs.copy()  # Track beliefs across steps

        for child in node.children:
            child_traces = execution_trace(child, current_beliefs, goal, current_trace)
            if not child_traces:  # If any child fails, the whole sequence fails
                return []

            # Take the first successful path (expand to all if needed)
            current_trace = child_traces[0]

            # Update beliefs for next step
            if hasattr(current_trace[-1], "post"):
                current_beliefs.update(set(current_trace[-1].post))

        return [current_trace]  # Return the successful execution trace

    return trace  # Return execution trace
    

def pick_lowest_cost_trace(tracelist, importance):
    if not tracelist:
        return []

    trace_cost = {}

    # Compute cost for each trace
    for i, trace in enumerate(tracelist):
        cost = np.array([0, 0, 0])
        for node in trace:
            if node.type == "ACT":
                cost = cost + np.array(node.costs)
        trace_cost[i] = cost  # Store cost with index

    # Get priority order for sorting
    priority_order = importance[1]

    # Sort traces based on priority order
    sorted_costs = sorted(trace_cost.items(), key=lambda item: tuple(item[1][i] for i in priority_order))

    # Find traces with the best (lowest) cost
    best_cost = sorted_costs[0][1]  # Best cost from sorted list
    best_traces_indices = [idx for idx, cost in sorted_costs if np.array_equal(cost, best_cost)]

    # Select one randomly if multiple have the same lowest cost
    selected_trace_index = random.choice(best_traces_indices) if len(best_traces_indices) > 1 else best_traces_indices[0]

    # Convert nodes to their names
    selected_trace = [([node.name for node in tracelist[selected_trace_index]], trace_cost[selected_trace_index])]
    # Get non-selected traces (excluding the selected one), with costs
    non_selected_traces = [([node.name for node in tracelist[idx]], trace_cost[idx]) 
                           for idx, _ in sorted_costs if idx != selected_trace_index]

    return selected_trace, non_selected_traces #if non selected is empty no problem?

def generate_explanation(trace, action_to_explain, root, norm, preferences, alt_trace=None):
    explanation = []
    action_node = None
    node_map = {node.name: node for node in PreOrderIter(root)}
    if action_to_explain not in node_map:
        return []  
    action_node = node_map[action_to_explain]
    trace_nodes = [node_map[name] for name in trace[0][0]]
    trace_names = trace[0][0]
    # for pre "P" factor
    before_action = trace_names[:trace_names.index(action_to_explain)+1]
    #"C", "V", "N", "F" Factors: OR-node explanations
    for node in trace_nodes:
        if node.type == "OR":
            selected = None
            non_selected = []
            for child in node.children:
                if child in trace_nodes:
                    selected = child
                else:
                    non_selected.append(child)

            if selected:
                explanation.append(["C", selected.name, list(getattr(selected, "pre", []))])
            for alt in non_selected:
              possible_factors = []
              if getattr(alt, "violation", False):
                  possible_factors.append(["N", alt.name, norm["type"] + "(" + ", ".join(norm["actions"]) + ")"])

              if not (hasattr(alt, "costs") or hasattr(selected, "costs")) and alt_trace is not None:
                # this is assuming there is always only 1 alternate trace. if there are multiple,
                # first search in which list this alt_node is, then assign according costs
                  alt_cost = alt_trace[0][1].tolist()
                  selected_cost = trace[0][1].tolist()
                  possible_factors.append(["V", selected.name, selected_cost, ">", alt.name, alt_cost])
              elif hasattr(alt,"costs") and hasattr(selected,"costs"):
                  possible_factors.append(["V", selected.name, selected.costs, ">", alt.name, alt.costs])

              if hasattr(alt, "pre") and not all(p in trace[0][0] for p in alt.pre):
                  possible_factors.append(["F", alt.name, [p for p in alt.pre if p not in trace[0][0]]])
              for x in possible_factors:
                selected_factor = possible_factors[0] if possible_factors else None
              if selected_factor:
                explanation.append(selected_factor)

        # add pre of nodes that came before action_node
        if node.type == "ACT" and hasattr(node, "pre"):
          if node.name in before_action:
            explanation.append(["P", node.name, list(node.pre)])

        # L factor: Link
        if node.name == action_to_explain:
            current_node = node
            while hasattr(current_node, "link") and current_node.link:  # Check if the node has a link
                for linked_node_name in current_node.link:
                    explanation.append(["L", current_node.name, "->", linked_node_name])
                    if linked_node_name in node_map:  # Ensure the linked node exists in the node dictionary
                        current_node = node_map[linked_node_name]  # Move to the next linked node)

    ## outside the loop ##
    # 4. "D" Factor: Goals
    current_node = action_node.parent  # Start from the immediate parent
    while current_node:  # Traverse upwards until there's no parent
        if current_node.type in ["AND", "SEQ", "OR"]:
            explanation.append(["D", current_node.name])
        current_node = current_node.parent


    # 5. "U" Factor: User Preferences
    explanation.append(["U", preferences])

    return explanation


root = build_annotated_tree(json_tree, norm)
tracelist = execution_trace(root, set(beliefs), goal)
if tracelist:
    selected, nonselected = pick_lowest_cost_trace(tracelist, preferences)
    selected_trace = selected[0][0]
    if nonselected:
        output = generate_explanation(selected,action_to_explain, root, norm, preferences, alt_trace=nonselected)
    else:
        output = generate_explanation(selected,action_to_explain, root, norm, preferences)
else:
    selected_trace = tracelist
    output = []