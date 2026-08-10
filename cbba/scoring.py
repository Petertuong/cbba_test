from .geometry import euclidean_distance

#time for an agent to move to each task from its current position
def compute_arrival_times(agent_position, path, tasks_dict):
    arrival_times = []
    current_position = agent_position
    current_time = 0.0
    for task_id in path:
        task_position = tasks_dict[task_id].position
        current_time += euclidean_distance(task_position, current_position)
        current_position = task_position
        arrival_times.append(current_time)

    return arrival_times

#compute the reward if travel to this task 
#(longer path may reduce the reward, but static_score determine its importance can outweigh distance)
def discount_reward(arrival_times, path, tasks_dict):
    total_score = 0.0

    for i, task_id in enumerate(path):
        tau = arrival_times[i]  # arrival time at this task
        c_bar = tasks_dict[task_id].static_score
        lambda_factor = tasks_dict[task_id].discount_factor
        discounted_value = (lambda_factor ** tau) * c_bar
        total_score += discounted_value
    return total_score


def marginal_score(agent_id, agent_dict, candidate_task_id, tasks_dict):
    bundle_i = agent_dict[agent_id].bundle
    path_i = agent_dict[agent_id].path
    agent_position = agent_dict[agent_id].position

    if candidate_task_id in bundle_i:
        return (0.0, -1)

    best_reward_j = 0.0
    best_position_j = -1

    curr_arrival_time = compute_arrival_times(agent_position, path_i, tasks_dict)
    prev_discount_reward = discount_reward(curr_arrival_time, path_i, tasks_dict)

    # Compute marginal score on each possible insertion
    for i in range(0, len(path_i) + 1):
        new_path = path_i.copy()
        new_path.insert(i, candidate_task_id)
        new_arrival_time = compute_arrival_times(agent_position, new_path, tasks_dict)
        new_discount_reward = discount_reward(new_arrival_time, new_path, tasks_dict)
        new_ms = new_discount_reward - prev_discount_reward

        if new_ms > best_reward_j:
            best_reward_j = new_ms
            best_position_j = i

    return (best_reward_j, best_position_j)
