"""
列生成的子问题求解器，针对每个人进行最低cost搜索
"""

from build_graph import node_id_2_node, Node, Edge, EdgeType



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



class GraphSearcher:
    def __init__(self):
        self.node_id_2_node = node_id_2_node

    def search(self, start_node_id: str, end_node_id: str) -> list[Node]:
        """
        Perform a search from start_node_id to end_node_id.
        This is a placeholder for the actual search algorithm.
        """
        # Implement the search logic here
        # For now, we will return an empty path
        return []