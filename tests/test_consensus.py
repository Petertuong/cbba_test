import pytest

from cbba import Agent
from cbba.consensus import resolve_task
from cbba.models import Message


def make_agents(z_ij, y_ij, z_kj, y_kj, s_i, s_k):
    """Builds a 4-agent dict for a single task j=0. i=0, k=1, m=2, n=3."""
    agent_dict = {a: Agent(a, (0, 0), num_tasks=1, num_agents=4) for a in range(4)}
    agent_dict[0].winning_agent_list[0] = z_ij
    agent_dict[0].winning_bid_list[0] = y_ij
    agent_dict[0].timestamp_list = list(s_i)
    agent_dict[1].winning_agent_list[0] = z_kj
    agent_dict[1].winning_bid_list[0] = y_kj
    agent_dict[1].timestamp_list = list(s_k)
    return agent_dict


def make_message(agent_dict, sender_id):
    sender = agent_dict[sender_id]
    return Message(
        sender_id,
        sender.winning_bid_list,
        sender.winning_agent_list,
        sender.timestamp_list,
    )


T = [0, 0, 0, 0]   # i and k equally informed
TK = [0, 0, 9, 9]  # k has fresher info about m(2) and n(3)
TI = [0, 0, 9, 9]  # i has fresher info about m(2) and n(3)

# name, z_ij, y_ij, z_kj, y_kj, s_i, s_k, expected_z, expected_y
CASES = [
    # sender (k) claims itself the winner
    ("r1_k_over_i_k_outbids",   0, 5.0, 1, 9.0, T, T, 1, 9.0),
    ("r1_k_over_i_k_underbids", 0, 9.0, 1, 5.0, T, T, 0, 9.0),
    ("r2_k_over_k",             1, 5.0, 1, 9.0, T, T, 1, 9.0),
    ("r3_k_over_m_k_fresher",   2, 9.0, 1, 5.0, T, TK, 1, 5.0),
    ("r3_k_over_m_k_outbids",   2, 5.0, 1, 9.0, T, T, 1, 9.0),
    ("r3_k_over_m_neither",     2, 9.0, 1, 5.0, TI, T, 2, 9.0),
    ("r4_k_over_none",         -1, 0.0, 1, 9.0, T, T, 1, 9.0),

    # sender (k) claims i is the winner
    ("r5_i_over_i",              0, 5.0, 0, 9.0, T, T, 0, 5.0),
    ("r6_i_over_k",               1, 5.0, 0, 9.0, T, T, -1, 0.0),
    ("r7_i_over_m_k_fresher",     2, 5.0, 0, 9.0, T, TK, -1, 0.0),
    ("r7_i_over_m_k_not_fresher", 2, 5.0, 0, 9.0, TI, T, 2, 5.0),
    ("r8_i_over_none",           -1, 0.0, 0, 9.0, T, T, -1, 0.0),

    # sender (k) claims a third agent m is the winner
    ("r9_m_over_i_fresh_and_high",   0, 5.0, 2, 9.0, T, TK, 2, 9.0),
    ("r9_m_over_i_fresh_only",       0, 9.0, 2, 5.0, T, TK, 0, 9.0),
    ("r10_m_over_k_fresher",         1, 5.0, 2, 9.0, T, TK, 2, 9.0),
    ("r10_m_over_k_not_fresher",     1, 5.0, 2, 9.0, TI, T, -1, 0.0),
    ("r11_m_over_m_fresher",         2, 5.0, 2, 9.0, T, TK, 2, 9.0),
    ("r11_m_over_m_not_fresher",     2, 5.0, 2, 9.0, TI, T, 2, 5.0),
    ("r12_m_over_n_both_fresh",      3, 5.0, 2, 9.0, T, TK, 2, 9.0),
    ("r12_m_over_n_reset",           3, 5.0, 2, 9.0, [0, 0, 9, 0], [0, 0, 0, 9], -1, 0.0),
    ("r13_m_over_none_fresher",     -1, 0.0, 2, 9.0, T, TK, 2, 9.0),
    ("r13_m_over_none_stale",       -1, 0.0, 2, 9.0, TI, T, -1, 0.0),

    # sender (k) has no claim
    ("r14_none_over_i",           0, 5.0, -1, 0.0, T, T, 0, 5.0),
    ("r15_none_over_k",           1, 5.0, -1, 0.0, T, T, -1, 0.0),
    ("r16_none_over_m_fresher",   2, 5.0, -1, 0.0, T, TK, -1, 0.0),
    ("r17_none_over_none",       -1, 0.0, -1, 0.0, T, T, -1, 0.0),
]


@pytest.mark.parametrize(
    "z_ij,y_ij,z_kj,y_kj,s_i,s_k,exp_z,exp_y",
    [c[1:] for c in CASES],
    ids=[c[0] for c in CASES],
)
def test_resolve_task_table(z_ij, y_ij, z_kj, y_kj, s_i, s_k, exp_z, exp_y):
    agent_dict = make_agents(z_ij, y_ij, z_kj, y_kj, s_i, s_k)
    msg = make_message(agent_dict, sender_id=1)

    resolve_task(agent_dict[0], msg, 0)

    assert agent_dict[0].winning_agent_list[0] == exp_z
    assert agent_dict[0].winning_bid_list[0] == pytest.approx(exp_y)
