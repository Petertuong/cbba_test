# Output of one agent, for monitoring and for the navigation/control side.
int32 agent_id
int32[] bundle                 # tasks in the order they were added (b_i)
int32[] path                   # tasks in execution order (p_i)
geometry_msgs/Point[] waypoints  # positions of the tasks in path order
int32 stable_rounds            # consecutive rounds with no change in bundle / z_i
