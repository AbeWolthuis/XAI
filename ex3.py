


# Algorithm sketch:
# Get all possible traces (adapt code from ex1 for all traces), but
# checking beliefs (newly implemented) and norms along the way (adapt code from ex2 for norms) 
# Store the cost of the trace with the trace
# Get all combinations of traces, such that the goal(s) are satisfied. 
# (Note: how to calculate these combinations?)
# For each goal-statisfying combination of traces, calculate the total cost (addition if multiple)
# Choose the trace with the lowest cost relative to the user's preference