'''runs only in colab or in prairielearn environment'''

from random import sample
from anytree import AnyNode
import numpy as np
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
        if hasattr(node, "post") and goal in node.post:
            return [trace + [node]]  # Goal achieved, return the trace
        elif not hasattr(node, "pre") or all(p in beliefs for p in node.pre):
            new_beliefs = beliefs.union(set(getattr(node, "post", [])))  # Update beliefs
            return [trace + [node]] 
        else:
            return []  # Preconditions not met, cannot execute

    # Handle OR nodes
    if node.type == "OR":
        total_traces = []
        for child in node.children:
            child_traces = execution_trace(child, beliefs.copy(), goal, trace + [node])
            total_traces.extend(child_traces)  # Collect all valid traces
        return total_traces

    # Handle SEQ nodes
    if node.type == "SEQ":
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


# if two traces have the same cost, pick random
def pick_lowest_cost_trace(tracelist, importance):
  if tracelist == []:
    return tracelist
  trace_cost = {}
  for trace in tracelist:
    cost = np.array([0,0,0])
    # compute cost in trace
    for node in trace:
      if node.type == "ACT":
        cost = cost + np.array(node.costs)
    position = tracelist.index(trace)
    trace_cost[position] = cost

  # costs are always [quality, price, time]
  priority_order = importance[1]

  sorted_costs = sorted(trace_cost.items(), key=lambda item: tuple(item[1][i] for i in priority_order))

  # Extract best cost traces (those with the same lowest cost)
  best_cost = sorted_costs[0][1]  # Best cost from sorted list
  best_traces_indices = [index for index, cost in sorted_costs if np.array_equal(cost, best_cost)]

    # Convert best traces to name lists
  
  final_list = [[node.name for node in tracelist[idx]] for idx in best_traces_indices]
  if len(final_list) > 1:
    final_list = sample(final_list, 1)
  else:
    return final_list[0]
  
root = build_annotated_tree(json_tree, norm)
tracelist = execution_trace(root, set(beliefs), goal)
if tracelist:
  output = pick_lowest_cost_trace(tracelist, preferences)
else:
  output = tracelist