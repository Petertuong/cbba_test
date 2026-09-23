# Consensus message broadcast by agent k (paper: y_k, z_k, s_k).
int32 sender_id
float64[] winning_bids         # y_k, indexed by task id
int32[] winning_agents         # z_k, indexed by task id, -1 = unassigned
float64[] timestamps           # s_k, indexed by agent id, -1 = never heard from
geometry_msgs/Point sender_position  # lets receivers simulate a limited comm range
