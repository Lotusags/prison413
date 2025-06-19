from collections import defaultdict
import bisect
from typing import Dict, List
from read_data import *
from enum import Enum

WAITING_TIME_LIMIT = 12 * 60 * 60  # 12 hours in seconds

class EdgeType(Enum):
    EDGE_IN_SAME_DUTY_DAY = 0
    EDGE_TO_NEXT_DUTY_DAY = 1
    EDGE_OVER_FLIGHT_CYCLE = 2

class Graph(object):
    pass


class Node(object):
    def __init__(self, event: Event):
        self.event = event
        self.out_edges: List[Edge] = []
        self.in_edges: List[Edge] = []
        self.source: str = event.source
        self.destination: str = event.destination
        self.st: datetime.datetime = event.st
        self.et: datetime.datetime = event.et
        # day num from epoch (January 1, 1970)
        self.start_day: int = event.st.toordinal()
        self.can_layover: bool = self.destination in layover_bases

    def __repr__(self):
        return f"Node({self.event.id_prefix}{self.event.base_id})"
    

class Edge(object):
    def __init__(self, source_node: Node, destination_node: Node, edge_type: EdgeType):

        self.source_node = source_node
        self.destination_node = destination_node
        self.type: EdgeType = edge_type
        self.passby_event: Event


flight_node_id_2_node: Dict[str, Node] = {}
ground_duty_node_id_2_node: Dict[str, Node] = {}
node_id_2_node: Dict[str, Node] = {}


def build_event_graph(
    flights: List[Flight],
    grounds: List[GroundDuty]
) -> Dict[str, List[str]]:
    event_destination_2_node_ids: Dict[str, List[str]] = defaultdict(list)
    event_source_2_node_ids: Dict[str, List[str]] = defaultdict(list)
    # 1. build nodes
    for flight in flights:
        node_id = f"{flight.id_prefix}{flight.base_id}"
        flight_node_id_2_node[node_id] = Node(flight)
        node_id_2_node[node_id] = flight_node_id_2_node[node_id]
        event_destination_2_node_ids[flight.destination].append(node_id)
        event_source_2_node_ids[flight.source].append(node_id)
    for ground in grounds:
        node_id = f"{ground.id_prefix}{ground.base_id}"
        ground_duty_node_id_2_node[node_id] = Node(ground)
        node_id_2_node[node_id] = ground_duty_node_id_2_node[node_id]
        event_destination_2_node_ids[ground.destination].append(node_id)
        event_source_2_node_ids[ground.source].append(node_id)
    for des, lst in event_destination_2_node_ids.items():
        lst.sort(key=lambda x: node_id_2_node[x].et)
    for source, lst in event_source_2_node_ids.items():
        lst.sort(key=lambda x: node_id_2_node[x].st)
    
    # 2. build edges
    # 2.1 try to find EDGE_IN_SAME_DUTY_DAY, which edge.source_node.destination == edge.destination_node.source && edge.destination_node.st >= edge.source_node.et && (edge.destination_node.st - edge.source_node.et) <= WAITING_TIME_LIMIT
    for destination, node_ids in event_destination_2_node_ids.items():
        if destination not in event_source_2_node_ids:
            continue
        for source_node_id in node_ids:
            source_node = node_id_2_node[source_node_id]
            et = source_node.et
            # use bisect to find the first node that starts after st
            idx = bisect.bisect_left(event_source_2_node_ids[destination], source_node_id, key=lambda x: node_id_2_node[x].st)
            # Iterate through all nodes starting after st
            for destination_node_id in event_source_2_node_ids[destination][idx:]:
                destination_node = node_id_2_node[destination_node_id]
                if destination_node.st >= source_node.et and (destination_node.st - source_node.et).total_seconds() <= WAITING_TIME_LIMIT:
                    edge_type = EdgeType.EDGE_IN_SAME_DUTY_DAY
                    edge = Edge(source_node, destination_node, edge_type)
                    source_node.out_edges.append(edge)
                    destination_node.in_edges.append(edge)
    return graph


# Example of usage after loading your data:
if __name__ == "__main__":
    flights = list(flight_id_2_flight.values())
    grounds = list(ground_id_2_ground.values())
    graph = build_event_graph(flights, grounds)
    # Now `graph` maps e.g. "Flt_10" → ["grd_5", "Flt_20", ...] depending on matches.
    # You can inspect:
    for src_id, dest_list in graph.items():
        print(f"{src_id} → {dest_list}")

