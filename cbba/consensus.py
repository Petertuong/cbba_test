from .models import Message


def resolve_task(agent_i, msg, j):

    i = agent_i.id
    k = msg.sender_id

    z_kj = msg.winning_agent_list[j]
    z_ij = agent_i.winning_agent_list[j]
    y_kj = msg.winning_bid_list[j]
    y_ij = agent_i.winning_bid_list[j]
    s_k = msg.timestamp_list
    s_i = agent_i.timestamp_list

    def receiver_action_k():
        if z_ij == i:
            if y_kj > y_ij:
                update(agent_i, j, msg)

        elif z_ij == k or z_ij == -1:
            update(agent_i, j, msg)

        else:
            m = z_ij
            if s_k[m] > s_i[m] or y_kj > y_ij:
                update(agent_i, j, msg)

    def receiver_action_i():
        if z_ij == i:
            pass
        elif z_ij == k:
            reset(agent_i, j)
        elif z_ij == -1:
            pass
        else:
            m = z_ij
            if s_k[m] > s_i[m]:
                reset(agent_i, j)

    def receiver_action_m():
        if z_ij == i:
            m = z_kj
            if s_k[m] > s_i[m] and y_kj > y_ij:
                update(agent_i, j, msg)

        elif z_ij == k:
            m = z_kj
            if s_k[m] > s_i[m]:
                update(agent_i, j, msg)
            else:
                reset(agent_i, j)

        elif z_ij == -1:
            m = z_kj
            if s_k[m] > s_i[m]:
                update(agent_i, j, msg)

        elif z_ij == z_kj:
            m = z_kj
            if s_k[m] > s_i[m]:
                update(agent_i, j, msg)

        else:
            m = z_kj
            n = z_ij

            if s_k[m] > s_i[m] and s_k[n] > s_i[n]:
                update(agent_i, j, msg)

            elif s_k[m] > s_i[m] and y_kj > y_ij:
                update(agent_i, j, msg)

            elif s_k[n] > s_i[n] and s_i[m] > s_k[m]:
                reset(agent_i, j)

    def receiver_action_none():
        if z_ij == i or z_ij == -1:
            pass

        elif z_ij == k:
            update(agent_i, j, msg)

        else:
            m = z_ij
            if s_k[m] > s_i[m]:
                update(agent_i, j, msg)

    # branch on what the sender thinks
    if z_kj == k:
        receiver_action_k()
    elif z_kj == i:
        receiver_action_i()
    elif z_kj == -1:
        receiver_action_none()
    else:
        receiver_action_m()


def release(agent_i):
    z_i = agent_i.winning_agent_list

    cut = -1

    #loop through bundle, find position where task is lost
    for pos, b_ij in enumerate(agent_i.bundle):

        if z_i[b_ij] != agent_i.id:
            cut = pos
            break
    #no lost task
    if cut == -1:
        return


    #release all the following tasks
    for b_ij in agent_i.bundle[cut:]:

        if z_i[b_ij] == agent_i.id:
            agent_i.set_winner(b_ij, -1, 0.0)

    del agent_i.bundle[cut:]
    agent_i.path = [t for t in agent_i.path if t in agent_i.bundle]



def update(agent_i, j, msg):

    z_kj = msg.winning_agent_list[j]
    y_kj = msg.winning_bid_list[j]

    agent_i.set_winner(j, z_kj, y_kj)


def reset(agent_i, j):

    agent_i.set_winner(j, -1, 0.0)

#Between 2 agents
#consumer
def consume_message(agent_i, msg):

    if msg is None:
        return

    for j in range(len(agent_i.winning_agent_list)):
        resolve_task(agent_i, msg, j)

    agent_i.timestamp_list[msg.sender_id] = msg.send_round

    #update timestamp based on which agent have higher vector
    for m in range(len(agent_i.timestamp_list)):
        if m != agent_i.id and m != msg.sender_id:
            agent_i.timestamp_list[m] = max(agent_i.timestamp_list[m], msg.timestamp_list[m])

#producer

def produce_message(agent_k, current_round):
    k_id = agent_k.id
    winning_bid_list = agent_k.winning_bid_list.copy()
    winning_agent_list = agent_k.winning_agent_list.copy()
    timestamp_list = agent_k.timestamp_list.copy()
    agent_k.timestamp_list[k_id] = current_round

    send_round = agent_k.timestamp_list[k_id]

    msg = Message(k_id, winning_bid_list,
            winning_agent_list, timestamp_list, send_round)

    return msg
