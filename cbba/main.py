from .consensus import produce_message, consume_message, release
from .bundle import build_bundle
from .models import Agent, Records, Task
from .transport import deliver_message
from .search_algo import bfs, build_graph


#assume static network
def main(graph, D, agent_dict, tasks_dict):
    current_round = 0
    N_u = len(agent_dict)
    L_t = 2 #capped task assigned per agent
    N_min = min(len(tasks_dict), N_u * L_t)

    Iteration = N_min * D

    converged = False #for debugging only

    while current_round < Iteration:
        old_bundle = []
        old_winning_agent_list = []
        message_list = [None] * N_u
        current_round += 1

        for agent_i in agent_dict.values():
            #save old state
            old_bundle.append(agent_i.bundle.copy())
            old_winning_agent_list.append(agent_i.winning_agent_list.copy())

            build_bundle(agent_i, tasks_dict, L_t)
            msg = produce_message(agent_i, current_round)
            message_list[agent_i.id] = msg

        inboxes = deliver_message(message_list, graph)
        

        for i, messages in inboxes.items():
            agent_i = agent_dict[i]
            for m in messages:
                consume_message(agent_i, m)
            release(agent_i)
        
        convergence = True 

        for agent_i in agent_dict.values():
            #index == id
            if (old_bundle[agent_i.id] != agent_i.bundle or 
                old_winning_agent_list[agent_i.id] != agent_i.winning_agent_list):
                
                convergence = False
            
        if convergence:
            converged = convergence
            break
        
    return (converged, current_round, N_min)

#for debugging as well since we are testing on multiple comm ranges
def make_agents():
    positions = [(0.0, 0.0), (500.0, 0.0), (1000.0, 0.0)]
    return {i: Agent(i, pos, len(tasks_dict), len(positions))
            for i, pos in enumerate(positions)}


def add_record(records, converged, disconnected, T_c, N_min, D, comm_range):
    records[comm_range] = Records(...)


records = {}

for comm_range in [3, 6, 9, 12, 15, 20]:
    agent_dict = make_agents()
    graph = build_graph(agent_dict, comm_range)
    disconnected , D  = bfs(N_u, graph) #longest hop + if graph is disconnected
    converged, T_c, N_min = main(graph, D)
    add_record(records, converged, disconnected, T_c, N_min, D, comm_range)

