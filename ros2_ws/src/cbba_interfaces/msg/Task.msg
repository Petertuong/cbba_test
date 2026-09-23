# One task in the environment. Ids must be 0..N-1 (the algorithm indexes lists by id).
int32 id
geometry_msgs/Point position
float64 static_score      # c_bar_j
float64 discount_factor   # lambda_j
