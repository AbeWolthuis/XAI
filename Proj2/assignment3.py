'''run only in colab or in prairielearn environment'''


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

def execution_trace(node, beliefs, goal, trace=None, alltraces = []):
    if trace is None:
        trace = []  # Start with an empty execution trace
    
    if node.violation == True:
      return []

    # Base case: if goal is achieved, return the trace
    if node.type == "ACT":
      if hasattr(node, "post") and node.post == goal:
        trace = trace + [node]
        return [trace]  
      # check preconditions
      elif not hasattr(node, "pre") or any(p in beliefs for p in node.pre):
        trace = trace + [node]
        return [trace] 
    
    # If this node has preconditions, check if they match current beliefs
    if hasattr(node, "pre") and not any(p in beliefs for p in node.pre):
          return []  # Cannot execute this node

    # SEQ and AND nodes: Execute children **in order**
    if node.type in ["SEQ", "AND"]:
        ordered_children = sorted(node.children, key=lambda x: getattr(x, "sequence", float("inf")))
        current_trace = trace + [node]
        for i, child in enumerate(ordered_children):
            if child.type == "OR":
                # OR child: Add OR node first, then pick a valid child path
                temp_trace = [child]  # Start with the OR node
                for or_child in child.children:
                    or_traces = execution_trace(or_child, beliefs, goal, temp_trace, alltraces)
                    if or_traces:
                        temp_trace = or_traces[0]  # Pick first valid OR path
                        break  # Stop after picking a valid OR branch

                current_trace = current_trace + temp_trace  # Update trace with OR path

            else:
                # Normal execution
                new_traces = execution_trace(child, beliefs, goal, current_trace, alltraces)
                if new_traces:
                    current_trace = new_traces[0]

        alltraces.append(current_trace)

    # try all paths
    if node.type == "OR":
        for child in node.children:
            child_traces = execution_trace(child, beliefs, goal, trace + [node], alltraces)
            

    return alltraces  # Return all valid execution traces

def pick_lowest_cost_trace(tracelist, importance):
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
  return final_list[0] if len(final_list) == 1 else final_list
  
root = build_annotated_tree(json_tree, norm)
tracelist = execution_trace(root, beliefs, goal)
if tracelist:
  output = pick_lowest_cost_trace(tracelist, preferences)
else:
  output = tracelist