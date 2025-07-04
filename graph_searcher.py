"""
列生成的子问题求解器，针对每个人进行最低cost搜索
"""

from build_graph import *
from read_data import *
from typing import List, Dict

# 有必要分crew建图嘛？
graph_of_crew: Dict[str, List[Node]] = {}


# show graph
def show_graph():
    total_edge_num = 0
    for node_id, node in node_id_2_node.items():
        display_string = ""
        display_string += f"Node ID: {node.event.base_id}, Node: {node.event.source} to {node.event.destination}, Start: {node.event.st}, End: {node.event.et} "
        duty_in_edge_num = sum(1 for edge in node.out_edges if edge.type == EdgeType.EDGE_IN_SAME_DUTY_DAY)
        display_string += f"  Duty in edges: {duty_in_edge_num}"
        duty_over_edge_num = sum(1 for edge in node.out_edges if edge.type == EdgeType.EDGE_TO_NEXT_DUTY_DAY)
        display_string += f", Duty over edges: {duty_over_edge_num}"
        cycle_edge_num = sum(1 for edge in node.out_edges if edge.type == EdgeType.EDGE_OVER_FLIGHT_CYCLE)
        display_string += f",  Cycle edges: {cycle_edge_num}"
        illegal_edge_num = sum(1 for edge in node.out_edges if edge.type == EdgeType.EDGE_ILLEGAL)
        display_string += f",  Illegal edges: {illegal_edge_num}"
        if duty_in_edge_num <= 3:
            print(display_string)
        total_edge_num += len(node.out_edges)
    print("Total nodes:", len(node_id_2_node))
    print("Total edges:", total_edge_num)


show_graph()



"""
对偶变量1 对应path中每个点的reduce cost，为负，不区分是哪个crew
对偶变量2，对应每个crew选取的reduce cost， 为正
对偶变量3，对应每个过夜机场的reduce cost， 为正，不区分是哪个crew
对偶变量4，对应每个新的日历日工作的reduce cost，这个需要区分是哪个crew
由于node中没有休息的node，因此需要检查每个crew是否有休息的置位，如果有，需要优先安排在对应时段进行休息
"""


class Path:
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.path: List[Node] = []
        self.working_days: List[int] = []  # 工作的日历日
        self.reduce_cost: float = 0.0  # 总的reduce cost
        self.layover_airport: List[str] = []  # 过夜机场列表


class GraphSearcher:
    def __init__(self):
        self.node_id_2_node = node_id_2_node
        self.node_id_2_reduce_cost: Dict[str, float] = {}
        self.crew_id_2_reduce_cost: Dict[str, float] = {}
        self.overnight_airport_2_reduce_cost: Dict[str, float] = {}
        self.crew_day_2_reduce_cost: Dict[str, Dict[int, float]] = {}  # crew_id -> day -> reduce cost

    def search(self, node_id_2_reduce_cost, crew_id_2_reduce_cost, overnight_airport_2_reduce_cost, crew_day_2_reduce_cost) -> List[List[Node]]:
        self.crew_id_2_reduce_cost = crew_id_2_reduce_cost
        self.node_id_2_reduce_cost = node_id_2_reduce_cost
        self.overnight_airport_2_reduce_cost = overnight_airport_2_reduce_cost
        self.crew_day_2_reduce_cost = crew_day_2_reduce_cost
        ans: List[List[Node]] = []
        # 需要返回各项参数 包括path是对应哪些点的，path是归属哪个crew的，
        for crew_id in crew_id_2_crew.keys():
            tmp_path = self.search_for_crew(crew_id)
            if tmp_path:
                ans.append(tmp_path)
        return ans
    
    def search_for_crew(self, crew_id: str) -> List[Node]:
        """
        Search for the path for a specific crew member.
        """
        # Implement the search logic here
        # For now, we will return an empty path
        return []
    
