class Agent:
    def __init__(self, agent_id, position, num_tasks, num_agents):
        self.id = agent_id
        self.position = position
        self.bundle = []  # task id goes here
        self.path = []  # task id goes here
        self.winning_agent_list = [-1] * num_tasks
        self.winning_bid_list = [0.0] * num_tasks
        self.topology = [[0] * num_agents ] * num_agents
        self.timestamp_list = [-1] * num_agents

    def set_winner(self, j, agent_id, bid):
        self.winning_agent_list[j] = agent_id
        self.winning_bid_list[j] = bid

    def set_path(self, index, task_id):
        self.path.insert(index, task_id)
    
    def set_bundle(self, task_id):
        self.bundle.append(task_id)
        

class Task:
    def __init__(self, task_id, position, static_score, discount_factor):
        self.id = task_id
        self.position = position
        self.static_score = static_score
        self.discount_factor = discount_factor
