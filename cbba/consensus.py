def resolve_task(i, k, j, agent_dict):
    z_kj = agent_dict[k].winning_agent_list[j]
    z_ij = agent_dict[i].winning_agent_list[j]
    y_kj = agent_dict[k].winning_bid_list[j]
    y_ij = agent_dict[i].winning_bid_list[j]
    s_k = agent_dict[k].timestamp_list
    s_i = agent_dict[i].timestamp_list

    def receiver_action_k():
        if z_ij == i:
            if y_kj > y_ij:
                update(i, k, j, agent_dict)

        elif z_ij == k or z_ij == -1:
            update(i, k, j, agent_dict)

        else:
            m = z_ij
            if s_k[m] > s_i[m] or y_kj > y_ij:
                update(i, k, j, agent_dict)

    def receiver_action_i():
        if z_ij == i:
            pass
        elif z_ij == k:
            reset(i, j, agent_dict)
        elif z_ij == -1:
            pass
        else:
            m = z_ij
            if s_k[m] > s_i[m]:
                reset(i, j, agent_dict)

    def receiver_action_m():
        if z_ij == i:
            m = z_kj
            if s_k[m] > s_i[m] and y_kj > y_ij:
                update(i, k, j, agent_dict)

        elif z_ij == k:
            m = z_kj
            if s_k[m] > s_i[m]:
                update(i, k, j, agent_dict)
            else:
                reset(i, j, agent_dict)

        elif z_ij == -1:
            m = z_kj
            if s_k[m] > s_i[m]:
                update(i, k, j, agent_dict)

        elif z_ij == z_kj:
            m = z_kj
            if s_k[m] > s_i[m]:
                update(i, k, j, agent_dict)

        else:
            m = z_kj
            n = z_ij

            if s_k[m] > s_i[m] and s_k[n] > s_i[n]:
                update(i, k, j, agent_dict)

            elif s_k[m] > s_i[m] and y_kj > y_ij:
                update(i, k, j, agent_dict)

            elif s_k[n] > s_i[n] and s_i[m] > s_k[m]:
                reset(i, j, agent_dict)

    def receiver_action_none():
        if z_ij == i or z_ij == -1:
            pass

        elif z_ij == k:
            update(i, k, j, agent_dict)

        else:
            m = z_ij
            if s_k[m] > s_i[m]:
                update(i, k, j, agent_dict)

    # branch on what the sender thinks
    if z_kj == k:
        receiver_action_k()
    elif z_kj == i:
        receiver_action_i()
    elif z_kj == -1:
        receiver_action_none()
    else:
        receiver_action_m()

def release(i, agent_dict):
    agent_i = agent_dict[i]
    z_i = agent_i.winning_agent_list

    cut = -1

    #loop through bundle, find position where task is lost
    for pos, b_ij in enumerate(agent_i.bundle):

        if z_i[b_ij] != i:
            cut = pos
            break
    #no lost task
    if cut == -1:
        return


    #release all the following tasks
    for b_ij in agent_i.bundle[cut:]:

        if z_i[b_ij] == i:
            agent_i.set_winner(b_ij, -1, 0.0)

    del agent_i.bundle[cut:]
    agent_i.path = [t for t in agent_i.path if t in agent_i.bundle]



def update(i, k, j, agent_dict):

    z_kj = agent_dict[k].winning_agent_list[j]
    y_kj = agent_dict[k].winning_bid_list[j]

    agent_i = agent_dict[i]
    agent_i.set_winner(j, z_kj, y_kj)


def reset(i, j, agent_dict):
    agent_i = agent_dict[i]

    agent_i.set_winner(j, -1, 0.0)

#Between 2 agents
def resolve_tasks(i, k, agent_dict, tasks_dict, current_round):
    agent_i = agent_dict[i]
    agent_k = agent_dict[k]

    g_i = agent_i.topology

    for j in tasks_dict:
        resolve_task(i, k, j, agent_dict)
    
    agent_i.timestamp_list[k] = current_round

    #update timestamp based on which agent have higher vector
    for m in range(len(agent_i.timestamp_list)):
        if m != i and m != k:
            agent_i.timestamp_list[m] = max(agent_i.timestamp_list[m], agent_k.timestamp_list[m])
        
    release(i, agent_dict)

