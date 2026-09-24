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
def make_tasks():
    positions = [(100.0, 100.0), (400.0, 200.0), (600.0, 100.0), (900.0, 300.0), (200.0, 800.0)]
    return {j: Task(j, pos, 1.0, 0.95) for j, pos in enumerate(positions)}


def make_agents(num_tasks):
    positions = [(0.0, 0.0), (500.0, 0.0), (1000.0, 0.0)]
    return {i: Agent(i, pos, num_tasks, len(positions))
            for i, pos in enumerate(positions)}


def add_record(records, converged, disconnected, T_c, N_min, D, comm_range):
    records[comm_range] = Records(converged, disconnected, T_c, N_min, D, comm_range)


#only runs with `python3 -m cbba.main`, not on import
if __name__ == "__main__":
    records = {}

    #agents are 500 apart: 400 = nobody connected, 600 = chain 0-1-2, 1100 = everyone
    for comm_range in [400, 600, 1100]:
        tasks_dict = make_tasks()
        agent_dict = make_agents(len(tasks_dict))
        graph = build_graph(agent_dict, comm_range)
        disconnected, D = bfs(len(agent_dict), graph) #longest hop + if graph is disconnected
        converged, T_c, N_min = main(graph, D, agent_dict, tasks_dict)
        add_record(records, converged, disconnected, T_c, N_min, D, comm_range)

    for comm_range, r in records.items():
        print("comm_range %5d: D=%d disconnected=%s converged=%s rounds=%d ratio=%s"
              % (comm_range, r.D, r.disconnected, r.converged, r.T_c, r.get_ratio()))

