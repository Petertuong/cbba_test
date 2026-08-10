from .consensus import resolve_tasks
from .bundle import build_bundle
from .models import Agent, Task

agent_topology = [  [1,1,0],
                    [1,1,1], 
                    [0,1,1] ]

tasks_dict = {
    0: Task(0, (2, 3),  static_score=10, discount_factor=0.95),
    1: Task(1, (8, 1),  static_score=25, discount_factor=0.95),
    2: Task(2, (5, 7),  static_score=15, discount_factor=0.95),
    3: Task(3, (1, 9),  static_score=20, discount_factor=0.95),
    4: Task(4, (9, 8),  static_score=12, discount_factor=0.95),
}

agent_dict = {
    0: Agent(0, (0, 0), num_tasks=5, num_agents=3),
    1: Agent(1, (5, 0), num_tasks=5, num_agents=3),
    2: Agent(2, (10, 0), num_tasks=5, num_agents=3),
}

L_t = 2 #capped task assigned per agent
D = 2 #longest hop between agent (breadth first search)

iteration = min(len(tasks_dict), len(agent_dict) * L_t) * D

def main():
    current_round = 0

#build_bundle(i, agent_dict, tasks_dict, L_t
 # @i: current_agent id
 # @agent_dict: list of all agents id
 # @tasks_dict: list of all tasks id
 # @L_t: int, max number of tasks per agent
    while current_round < iteration:
        current_round += 1

        for i in agent_dict:
            build_bundle(i, agent_dict, tasks_dict, L_t)
        
    # resolve_tasks(i, k, agent_dict, tasks_dict, current_round):
        # @i, @k: agent i receiver and agent k sender id
        
        for i in agent_dict:
            for k in agent_dict:
                if i == k:
                    continue
                elif agent_topology[i][k] == 1:
                    resolve_tasks(i,k, agent_dict, tasks_dict, current_round)
