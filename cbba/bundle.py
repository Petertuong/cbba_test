from .scoring import marginal_score

#loop through every task, find the best task
def bundle_construction(agent_i, tasks_dict):

    winning_bid_list_i = agent_i.winning_bid_list

    best_task_id = -1 #final best task
    best_reward = 0.0  # final best reward
    best_position = -1  # position to be inserted

    for j in tasks_dict:
        (best_reward_j, best_position_j) = marginal_score(agent_i, j, tasks_dict)
        if best_position_j == -1: #if all tasks are in the bundle
            continue
        if best_reward_j > winning_bid_list_i[j] and best_reward_j > best_reward:
            best_reward = best_reward_j
            best_task_id = j
            best_position = best_position_j

    #if all tasks added or no tasks can outweigh winning bid
    if best_task_id == -1:
        return False

    agent_i.set_bundle(best_task_id)
    agent_i.set_path(best_position, best_task_id)
    agent_i.set_winner(best_task_id, agent_i.id, best_reward)

    return True

#loop through every task in bundle
def build_bundle(agent_i, tasks_dict, L_t):
    bundle_i = agent_i.bundle

    while len(bundle_i) < L_t:
        success = bundle_construction(agent_i, tasks_dict)
        if not success:
            break
