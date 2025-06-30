from collections import defaultdict
import bisect
from typing import Dict, List, Tuple
from read_data import *
from enum import Enum
from sortedcontainers import SortedList

WAITING_TIME_LIMIT = 4 * 60 * 60  # 12 hours in seconds
DUTY_DAY_GAP = 12 * 60 * 60
WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT = 3 * 60 * 60  # 3 hours in seconds
WAITING_TIME_BETWEENT_BUS_AND_FLIGHT = 2 * 60 * 60  # 2 hours in seconds
CYCLE_DAY_GAP = 2
CYCLE_WAIT_DAY_MAX_GAP = 4
LEGAL_DEADHEAD_COST = 0.5


# todo passby event 的选择优化，现在是最早到达时间，但这个其实是不对的，应该是针对每个到达时刻的最晚起飞时间  线段树搞一下

class EdgeType(Enum):
    EDGE_IN_SAME_DUTY_DAY = 0
    EDGE_TO_NEXT_DUTY_DAY = 1
    EDGE_OVER_FLIGHT_CYCLE = 2
    EDGE_ILLEGAL = 3

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
        self.fly_time: int = event.fly_time if isinstance(event, Flight) else 0
        # day num from epoch (January 1, 1970)
        self.start_day: int = event.st.toordinal()
        self.end_day: int = event.et.toordinal()
        self.can_layover: bool = self.destination in layover_bases
        

    def __repr__(self):
        return f"Node({self.event.base_id})"
    

class Edge(object):
    def __init__(self, source_node: Node, destination_node: Node, edge_type: EdgeType):

        self.source_node = source_node
        self.destination_node = destination_node
        self.type: EdgeType = edge_type
        self.passby_event: List[Event] = []
        self.time_cost: float = (destination_node.st - source_node.et).total_seconds()
        self.day_cost: int = (destination_node.start_day - source_node.end_day)
        self.penalty_of_illegal_layover: int = 0
        # 这个要根据人来，搞不了
        self.penalty_of_legal_layover: int = 0
        self.penalty_of_deadhead: float = 0.0

    def __repr__(self):
        return f"Edge({self.source_node.event.base_id} -> {self.destination_node.event.base_id}, type={self.type})"


flight_node_id_2_node: Dict[str, Node] = {}
ground_duty_node_id_2_node: Dict[str, Node] = {}
node_id_2_node: Dict[str, Node] = {}
# Maps for event destinations and sources to their node IDs
event_destination_2_node_ids: Dict[str, List[str]] = defaultdict(list)
event_source_2_node_ids: Dict[str, List[str]] = defaultdict(list)
bus_source_2_node_ids: Dict[str, List[str]] = defaultdict(list)
bus_destination_2_node_ids: Dict[str, List[str]] = defaultdict(list)
flight_source_2_node_ids: Dict[str, List[str]] = defaultdict(list)
flight_destination_2_node_ids: Dict[str, List[str]] = defaultdict(list)

def check_is_the_same_aircraft(source_node: Node, destination_node: Node) -> bool:
    if isinstance(source_node.event, Flight) and isinstance(destination_node.event, Flight):
        return source_node.event.aircraftNo == destination_node.event.aircraftNo
    else:
        return True
        
def build_edge_in_the_same_duty_day():
        
    for destination, node_ids in event_destination_2_node_ids.items():
        if destination not in event_source_2_node_ids:
            continue
        for source_node_id in node_ids:
            source_node = node_id_2_node[source_node_id]
            et = source_node.et
            # use bisect to find the first node that starts after st
            idx = bisect.bisect_left(event_source_2_node_ids[destination], et, key=lambda x: node_id_2_node[x].st)
            # Iterate through all nodes starting after st
            for destination_node_id in event_source_2_node_ids[destination][idx:]:
                destination_node = node_id_2_node[destination_node_id]
                # if both is flight node, need to check if aircraftNo is same
                time_need_to_wait = WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT if not check_is_the_same_aircraft(source_node, destination_node) else 0
                        
                if WAITING_TIME_LIMIT >= (destination_node.st - source_node.et).total_seconds() >= time_need_to_wait:
                    edge_type = EdgeType.EDGE_IN_SAME_DUTY_DAY
                    edge = Edge(source_node, destination_node, edge_type)
                    source_node.out_edges.append(edge)
                    destination_node.in_edges.append(edge)
                elif (destination_node.st - source_node.et).total_seconds() > WAITING_TIME_LIMIT:
                    break



def build_edge_to_next_duty_day():
    def build_edge_no_over_day_in_same_airport():
        """
        source_node.destination == destination_node.source && edge.destination_node.st >= edge.source_node.et + DUTY_DAY_GAP
        """
        for destination, node_ids in event_destination_2_node_ids.items():
            edge_type = None
            if destination not in event_source_2_node_ids:
                continue
            if destination not in layover_bases:
                # 允许违禁  每一个新增机场扣一次分，感觉惩罚不是很重？
                edge_type = EdgeType.EDGE_ILLEGAL
            for source_node_id in node_ids:
                source_node = node_id_2_node[source_node_id]
                et = source_node.et
                # use bisect to find the first node that starts after st
                idx = bisect.bisect_left(event_source_2_node_ids[destination], et + datetime.timedelta(seconds=DUTY_DAY_GAP), key=lambda x: node_id_2_node[x].st)
                # Iterate through all nodes starting after st
                for destination_node_id in event_source_2_node_ids[destination][idx:]:
                    destination_node = node_id_2_node[destination_node_id]
                    if WAITING_TIME_LIMIT + DUTY_DAY_GAP >= (destination_node.st - source_node.et).total_seconds():
                        edge_type = EdgeType.EDGE_TO_NEXT_DUTY_DAY if not edge_type else edge_type
                        edge = Edge(source_node, destination_node, edge_type)
                        source_node.out_edges.append(edge)
                        destination_node.in_edges.append(edge)
                    else:
                        break

    def build_edge_with_deadhead():
        all_build_num = 0
        """
        source_node.destination != destination_node.source, so we need to deadhead
        如果是结束执勤日的置位，仅允许在可过夜机场，且结束置位时间与开始置位时间间隔大于等于12小时
        如果是开始执勤日的置位，要求起点终点在可过夜机场，起点结束时间与置位开始时间间隔大于等于12小时，且置位后需考虑休息
        """
        for destination, node_ids in event_destination_2_node_ids.items():
            # 1. 考虑前一执勤日结束时进行置位
            # 针对执勤日结束置位，不需要考虑开始时间，开始时间只要满足最小间隔即可，到达时间越早越好
            # 但需要区分飞行和大巴，因为有统计时间口径上的不一样，因此应该分开来考虑
            # 加两条边？
            for source_node_id in node_ids:
                # 前两个是bus的最短到达时间，后两个是飞行航班的最短到达时间
                time_arrived_nxt_airport: Dict[str, Tuple[datetime.datetime, str, datetime.datetime, str]] = defaultdict(lambda: (datetime.datetime.max, "", datetime.datetime.max, ""))
                source_node = node_id_2_node[source_node_id]
                et = source_node.et
                # 1.1 考虑大巴置位
                if destination in bus_source_2_node_ids:
                    idx = bisect.bisect_left(bus_source_2_node_ids[destination], et + datetime.timedelta(seconds=WAITING_TIME_BETWEENT_BUS_AND_FLIGHT), key=lambda x: bus_id_2_bus[x].st)
                    for bus_id in bus_source_2_node_ids[destination][idx:]:
                        bus = bus_id_2_bus[bus_id]
                        # if bus.destination not in layover_bases:
                        #     continue
                        if (bus.st - source_node.et).total_seconds() > WAITING_TIME_BETWEENT_BUS_AND_FLIGHT + WAITING_TIME_LIMIT:
                            break
                        if time_arrived_nxt_airport[bus.destination][0] > bus.et:
                            prime_passby = time_arrived_nxt_airport[bus.destination]
                            time_arrived_nxt_airport[bus.destination] = (bus.et, bus_id, prime_passby[2], prime_passby[3])
                # 1.2 考虑航班置位
                if destination in flight_source_2_node_ids:
                    idx = bisect.bisect_left(flight_source_2_node_ids[destination], et, key=lambda x: node_id_2_node[x].st)
                    for flight_id in flight_source_2_node_ids[destination][idx:]:
                        flight = node_id_2_node[flight_id]
                        # if flight.destination not in layover_bases:
                        #     continue
                        # if both is flight node, need to check if aircraftNo is same
                        time_need_to_wait = WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT if not check_is_the_same_aircraft(source_node, flight) else 0  
                        if WAITING_TIME_LIMIT >= (flight.st - source_node.et).total_seconds() >= time_need_to_wait:
                            if time_arrived_nxt_airport[flight.destination][2] > flight.et:
                                prime_passby = time_arrived_nxt_airport[flight.destination]
                                time_arrived_nxt_airport[flight.destination] = (prime_passby[0], prime_passby[1], flight.et, flight_id)
                        elif (flight.st - source_node.et).total_seconds() > WAITING_TIME_LIMIT:
                            break
                # 1.3 从新到达的位置开始检查，是否有可以创建的边
                # print("source_node: " + source_node.event.base_id + " can go to " + str(len(time_arrived_nxt_airport)) + " airports by passby in prev day")
                cnt = 0
                for new_airport, time_arrived in time_arrived_nxt_airport.items():
                    if new_airport not in event_source_2_node_ids:
                        continue
                    min_st, max_st = min(time_arrived[0], time_arrived[2]), max(time_arrived[0], time_arrived[2])
                    idx = bisect.bisect_left(event_source_2_node_ids[new_airport], min_st + datetime.timedelta(seconds=DUTY_DAY_GAP), key=lambda x: node_id_2_node[x].st)
                    # tmp_idx = bisect.bisect_left(event_source_2_node_ids[new_airport], time_arrived[0] + datetime.timedelta(seconds=DUTY_DAY_GAP + WAITING_TIME_LIMIT), key=lambda x: node_id_2_node[x].st)
                    # print("----------- idx: " + str(idx) + ", tmp_idx: " + str(tmp_idx))
                    if new_airport in layover_bases:
                        edge_type = EdgeType.EDGE_TO_NEXT_DUTY_DAY
                    else:
                        edge_type = EdgeType.EDGE_ILLEGAL
                    for destination_node_id in event_source_2_node_ids[new_airport][idx:]:
                        destination_node = node_id_2_node[destination_node_id]
                        is_add = False
                        if time_arrived[0] + datetime.timedelta(seconds=DUTY_DAY_GAP) < destination_node.st < time_arrived[0] + datetime.timedelta(seconds=DUTY_DAY_GAP + WAITING_TIME_LIMIT):
                            passby_event = bus_id_2_bus[time_arrived[1]]                           
                            edge = Edge(source_node, destination_node, edge_type)
                            edge.passby_event.append(passby_event)
                            edge.penalty_of_deadhead = len(edge.passby_event) * LEGAL_DEADHEAD_COST
                            source_node.out_edges.append(edge)
                            destination_node.in_edges.append(edge)
                            cnt += 1
                            is_add = True
                        if time_arrived[2] + datetime.timedelta(seconds=DUTY_DAY_GAP) < destination_node.st < time_arrived[2] + datetime.timedelta(seconds=DUTY_DAY_GAP + WAITING_TIME_LIMIT):
                            passby_event = flight_id_2_flight[time_arrived[3]]                           
                            edge = Edge(source_node, destination_node, edge_type)
                            edge.passby_event.append(passby_event)
                            edge.penalty_of_deadhead = len(edge.passby_event) * LEGAL_DEADHEAD_COST
                            source_node.out_edges.append(edge)
                            destination_node.in_edges.append(edge)
                            cnt += 1
                            is_add = True
                        if not is_add:
                            break
                # print(f"Build {cnt} edges from {source_node.event.base_id} to next duty day by passby in prev day")
                all_build_num += cnt
            # 2. 考虑后一执勤日开始时置位
            for source_node_id in node_ids:
                source_node = node_id_2_node[source_node_id]
                edge_type = None
                if source_node.destination not in layover_bases:
                    edge_type = EdgeType.EDGE_ILLEGAL
                # et\st\event_id
                time_arrived_nxt_airport_by_bus: Dict[str, List[Tuple[datetime.datetime, datetime.datetime, str]]] = defaultdict(list)
                # 还需要考虑飞机型号 讲道理飞行型号都不一样，应该不可能有多趟航班
                # important: 假设所有飞机型号，短时间内只有一趟置位
                time_arrived_nxt_airport_by_flight_counter_aircraft: Dict[str, Dict[str, Tuple[datetime.datetime, str]]] = defaultdict(lambda: defaultdict(lambda: (datetime.datetime.max, "")))
                time_arrived_nxt_airport_by_flight: Dict[str, List[Tuple[datetime.datetime, datetime.datetime, str]]] = defaultdict(list) 
                new_airport_set: Set[str] = set()
                et = source_node.et
                # 这个比较麻烦，需要在et满足后续st的条件下，寻找最早的st
                # 2.1 考虑大巴置位
                if destination in bus_source_2_node_ids:
                    idx = bisect.bisect_left(bus_source_2_node_ids[destination], et + datetime.timedelta(seconds=DUTY_DAY_GAP), key=lambda x: bus_id_2_bus[x].st)
                    for bus_id in bus_source_2_node_ids[destination][idx:]:
                        bus = bus_id_2_bus[bus_id]
                        if (bus.st - source_node.et).total_seconds() > DUTY_DAY_GAP + WAITING_TIME_LIMIT:
                            break
                        new_airport_set.add(bus.destination)
                        time_arrived_nxt_airport_by_bus[bus.destination].append((bus.et, bus.st, bus_id))
                # 2.2 考虑航班置位
                if destination in flight_source_2_node_ids:
                    idx = bisect.bisect_left(flight_source_2_node_ids[destination], et + datetime.timedelta(seconds=DUTY_DAY_GAP), key=lambda x: node_id_2_node[x].st)
                    for flight_id in flight_source_2_node_ids[destination][idx:]:
                        flight = node_id_2_node[flight_id]
                        if not isinstance(flight.event, Flight):
                            continue
                        aircraft = flight.event.aircraftNo
                        if WAITING_TIME_LIMIT + DUTY_DAY_GAP >= (flight.st - source_node.et).total_seconds():
                            new_airport_set.add(flight.destination)
                            if time_arrived_nxt_airport_by_flight_counter_aircraft[flight.destination][aircraft][0] > flight.et:
                                time_arrived_nxt_airport_by_flight_counter_aircraft[flight.destination][aircraft] = (flight.et, flight_id)
                            time_arrived_nxt_airport_by_flight[flight.destination].append((flight.et, flight.st, flight_id))
                        elif (flight.st - source_node.et).total_seconds() > WAITING_TIME_LIMIT + DUTY_DAY_GAP:
                            break
                # print("source_node: " + source_node.event.base_id + " can go to " + str(len(new_airport_set)) + " airports by passby in next day")
                # 2.3 更新到达每个机场的几个时间指标，优化时间复杂度
                # 这个字典是所有passby方式到达，假设都需要等待才能开始下阶段任务的最小时间
                # 具体使用需要再去查同飞机型号的是否存在，存在则不罚时取min
                cnt = 0
                # really_can_start_time_map: Dict[str, Tuple[datetime.datetime, str]] = defaultdict(lambda: (datetime.datetime.max, ""))
                # 只是一个最早时间的参考，从这个时间出发去搜索可能的下一条边
                min_time_arrived_map: Dict[str, datetime.datetime] = defaultdict(lambda: datetime.datetime.max)
                for new_airport in new_airport_set:
                    min_time_arrived = datetime.datetime.max
                    if new_airport in time_arrived_nxt_airport_by_bus:
                        # todo 验证下排序正确性
                        time_arrived_nxt_airport_by_bus[new_airport].sort()
                        min_time_arrived = min(min_time_arrived, time_arrived_nxt_airport_by_bus[new_airport][0][0])
                        # if really_can_start_time_map[new_airport][0] > time_arrived_nxt_airport_by_bus[new_airport][0][0] + datetime.timedelta(seconds=WAITING_TIME_BETWEENT_BUS_AND_FLIGHT):
                        #     really_can_start_time_map[new_airport] = (time_arrived_nxt_airport_by_bus[new_airport][0] + datetime.timedelta(seconds=WAITING_TIME_BETWEENT_BUS_AND_FLIGHT), time_arrived_nxt_airport_by_bus[new_airport][1])
                    if new_airport in time_arrived_nxt_airport_by_flight:
                        time_arrived_nxt_airport_by_flight[new_airport].sort()
                        min_time_arrived = min(min_time_arrived, time_arrived_nxt_airport_by_flight[new_airport][0][0])
                            # if really_can_start_time_map[new_airport][0] > time_arrived_by_aircraft[0] + datetime.timedelta(seconds=WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT):
                            #     really_can_start_time_map[new_airport] = (time_arrived_by_aircraft[0] + datetime.timedelta(seconds=WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT), time_arrived_by_aircraft[1])
                    min_time_arrived_map[new_airport] = min_time_arrived
                flight_max_st_index: Dict[str, List[int]] = defaultdict(list)
                bus_max_st_index: Dict[str, List[int]] = defaultdict(list)
                # 2.4 维护当前index及所有et更小的passby_event的最小st的index
                for new_airport in new_airport_set:
                    if new_airport in time_arrived_nxt_airport_by_bus and len(time_arrived_nxt_airport_by_bus[new_airport]) > 0:
                        bus_max_st_index[new_airport] = [0]
                        for i, (et, st, bus_id) in enumerate(time_arrived_nxt_airport_by_bus[new_airport][1:]):
                            print("还真有大于1的passby bus " + new_airport + min_time_arrived_map[new_airport].isoformat())
                            prime_max_st_idx = bus_max_st_index[new_airport][-1]
                            if st >= time_arrived_nxt_airport_by_bus[new_airport][prime_max_st_idx][1]:
                                bus_max_st_index[new_airport].append(i)
                            else:
                                bus_max_st_index[new_airport].append(prime_max_st_idx)
                    if new_airport in time_arrived_nxt_airport_by_flight and len(time_arrived_nxt_airport_by_flight[new_airport]) > 0:
                        flight_max_st_index[new_airport] = [0]
                        for i, (et, st, flight_id) in enumerate(time_arrived_nxt_airport_by_flight[new_airport][1:]):
                            print("还真有大于1的passby flight " + new_airport + min_time_arrived_map[new_airport].isoformat())
                            prime_max_st_idx = flight_max_st_index[new_airport][-1]
                            if st >= time_arrived_nxt_airport_by_flight[new_airport][prime_max_st_idx][1]:
                                flight_max_st_index[new_airport].append(i)
                            else:
                                flight_max_st_index[new_airport].append(prime_max_st_idx)

                # 2.5 对每个新机场，找到可以创建的边
                # bus和flight分开 所有满足et和st关系的，找最大st
                for new_airport, time_arrived in min_time_arrived_map.items():
                    if new_airport not in event_source_2_node_ids:
                        continue
                    idx = bisect.bisect_left(event_source_2_node_ids[new_airport], time_arrived, key=lambda x: node_id_2_node[x].st)
                    # bus 和 
                    for destination_node_id in event_source_2_node_ids[new_airport][idx:]:
                        destination_node = node_id_2_node[destination_node_id]
                        is_add = False
                        # 先考虑bus, bisect right 搜索
                        # 寻找et小于等于destination_node.st - WAITING_TIME_BETWEENT_BUS_AND_FLIGHT的最大st
                        time_limit_4_bus = WAITING_TIME_BETWEENT_BUS_AND_FLIGHT if isinstance(destination_node.event, Flight) else 0
                        the_latest_time_arrived_by_bus = destination_node.st - datetime.timedelta(seconds=time_limit_4_bus)
                        index_of_legal_bus = bisect.bisect_right(time_arrived_nxt_airport_by_bus[new_airport], (the_latest_time_arrived_by_bus, datetime.datetime.min, ""))
                        if index_of_legal_bus > 0:
                            passby_event_index = bus_max_st_index[new_airport][index_of_legal_bus - 1]
                            passby_event_id = time_arrived_nxt_airport_by_bus[new_airport][passby_event_index][2]
                            passby_event = bus_id_2_bus[passby_event_id]
                            edge_type = EdgeType.EDGE_TO_NEXT_DUTY_DAY if edge_type is None else edge_type
                            edge = Edge(source_node, destination_node, edge_type)
                            edge.passby_event.append(passby_event)
                            edge.penalty_of_deadhead = len(edge.passby_event) * LEGAL_DEADHEAD_COST
                            source_node.out_edges.append(edge)
                            destination_node.in_edges.append(edge)
                            is_add = True
                            cnt += 1
                        # 然后考虑flight
                        # 首先考虑所有型号的飞机
                        time_limit_4_flight = WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT if isinstance(destination_node.event, Flight) else 0
                        the_lastest_time_arrived_by_flight = destination_node.st - datetime.timedelta(seconds=time_limit_4_flight)
                        index_of_legal_flight = bisect.bisect_right(time_arrived_nxt_airport_by_flight[new_airport], (the_lastest_time_arrived_by_flight, datetime.datetime.min, ""))
                        if index_of_legal_flight > 0:
                            passby_event_index = flight_max_st_index[new_airport][index_of_legal_flight - 1]
                            passby_event_id = time_arrived_nxt_airport_by_flight[new_airport][passby_event_index][2]
                            passby_event = flight_id_2_flight[passby_event_id]
                            if isinstance(destination_node.event, Flight):
                            # 需要考虑飞机型号
                                curr_aircraft = destination_node.event.aircraftNo
                                if curr_aircraft in time_arrived_nxt_airport_by_flight_counter_aircraft[new_airport]:
                                    same_aircraft_flight_id = time_arrived_nxt_airport_by_flight_counter_aircraft[new_airport][curr_aircraft][1]
                                    if flight_id_2_flight[same_aircraft_flight_id].et < destination_node.st and flight_id_2_flight[same_aircraft_flight_id].st > passby_event.st:
                                        passby_event = flight_id_2_flight[same_aircraft_flight_id]
                            edge_type = EdgeType.EDGE_TO_NEXT_DUTY_DAY if edge_type is None else edge_type
                            edge = Edge(source_node, destination_node, edge_type)
                            edge.passby_event.append(passby_event)
                            edge.penalty_of_deadhead = len(edge.passby_event) * LEGAL_DEADHEAD_COST
                            source_node.out_edges.append(edge)
                            destination_node.in_edges.append(edge)
                            is_add = True
                            cnt += 1
                        if not is_add:
                            break
                        # print(f"Build edge {edge} with passby event {edge.passby_event}")
                # print(f"Build {cnt} edges from {source_node.event.base_id} to next duty day by passby in next day")
                all_build_num += cnt
        print(f"Total {all_build_num} edges built with deadhead in next duty day")
                        
    build_edge_no_over_day_in_same_airport()
    build_edge_with_deadhead()

    
def build_edge_to_next_cycle():
    def build_edge_in_same_base():
        """
        source_node.destination == destination_node.source && edge.destination_node.event.start_day - edge.source_node.et.event.end_day >= 2
        """
        for destination, node_ids in event_destination_2_node_ids.items():
            if destination not in crew_possible_bases:
                continue
            if destination not in event_source_2_node_ids:
                continue
            for source_node_id in node_ids:
                source_node = node_id_2_node[source_node_id]
                ed = source_node.end_day
                # use bisect to find the first node that starts after st
                idx = bisect.bisect_left(event_source_2_node_ids[destination], ed + CYCLE_DAY_GAP, key=lambda x: node_id_2_node[x].start_day)
                # Iterate through all nodes starting after st
                for destination_node_id in event_source_2_node_ids[destination][idx:]:
                    destination_node = node_id_2_node[destination_node_id]
                    if CYCLE_WAIT_DAY_MAX_GAP >= destination_node.start_day - source_node.end_day:
                        edge_type = EdgeType.EDGE_OVER_FLIGHT_CYCLE
                        edge = Edge(source_node, destination_node, edge_type)
                        source_node.out_edges.append(edge)
                        destination_node.in_edges.append(edge)
                    else:
                        break
        

    def build_edge_with_deadhead():
        """
        起点在基地 -> 终点不在基地，需置位
        起点不在基地 -> 终点在基地
        起点不在基地 -> 终点不在基地，需2次置位
        """
        all_build_num = 0
        for destination, node_ids in event_destination_2_node_ids.items():
            # 1. 考虑前一执勤日结束时进行置位
            for source_node_id in node_ids:
                time_arrived_nxt_airport: Dict[str, Tuple[datetime.datetime, str]] = defaultdict(lambda: (datetime.datetime.max, ""))
                source_node = node_id_2_node[source_node_id]
                et = source_node.et
                # 1.1 考虑大巴置位
                if destination in bus_source_2_node_ids:
                    idx = bisect.bisect_left(bus_source_2_node_ids[destination], et + datetime.timedelta(seconds=WAITING_TIME_BETWEENT_BUS_AND_FLIGHT), key=lambda x: bus_id_2_bus[x].st)
                    for bus_id in bus_source_2_node_ids[destination][idx:]:
                        bus = bus_id_2_bus[bus_id]
                        if bus.destination not in crew_possible_bases:
                            continue
                        if (bus.st - source_node.et).total_seconds() > WAITING_TIME_BETWEENT_BUS_AND_FLIGHT + WAITING_TIME_LIMIT:
                            break
                        if time_arrived_nxt_airport[bus.destination][0] > bus.et:
                            time_arrived_nxt_airport[bus.destination] = (bus.et, bus_id)
                # 1.2 考虑航班置位
                if destination in flight_source_2_node_ids:
                    idx = bisect.bisect_left(flight_source_2_node_ids[destination], et, key=lambda x: node_id_2_node[x].st)
                    for flight_id in flight_source_2_node_ids[destination][idx:]:
                        flight = node_id_2_node[flight_id]
                        if flight.destination not in crew_possible_bases:
                            continue
                        # if both is flight node, need to check if aircraftNo is same
                        time_need_to_wait = WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT if not check_is_the_same_aircraft(source_node, flight) else 0  
                        if WAITING_TIME_LIMIT >= (flight.st - source_node.et).total_seconds() >= time_need_to_wait:
                            if time_arrived_nxt_airport[flight.destination][0] > flight.et:
                                time_arrived_nxt_airport[flight.destination] = (flight.et, flight_id)
                        elif (flight.st - source_node.et).total_seconds() > WAITING_TIME_LIMIT:
                            break
                # print("source_node: " + source_node.event.base_id + " can go to " + str(len(time_arrived_nxt_airport)) + " airports by passby in prev day")
                # 1.3 从新到达的位置开始检查，是否有可以创建的边
                cnt = 0
                for new_airport, time_arrived in time_arrived_nxt_airport.items():
                    if new_airport not in event_source_2_node_ids:
                        continue
                    ed = time_arrived[0].toordinal()
                    idx = bisect.bisect_left(event_source_2_node_ids[new_airport], ed + CYCLE_DAY_GAP, key=lambda x: node_id_2_node[x].start_day)
                    for destination_node_id in event_source_2_node_ids[new_airport][idx:]:
                        destination_node = node_id_2_node[destination_node_id]
                        if CYCLE_WAIT_DAY_MAX_GAP >= destination_node.start_day - ed:
                            edge_type = EdgeType.EDGE_OVER_FLIGHT_CYCLE
                            edge = Edge(source_node, destination_node, edge_type)
                            event_id = time_arrived[1]
                            prefix = event_id.split("_")[0]
                            tmp = flight_id_2_flight[event_id] if prefix == "Flt" else bus_id_2_bus[event_id]
                            edge.passby_event.append(tmp)
                            edge.penalty_of_deadhead = len(edge.passby_event) * LEGAL_DEADHEAD_COST
                            source_node.out_edges.append(edge)
                            destination_node.in_edges.append(edge)
                            cnt += 1
                        else:
                            break
                # print(f"Build {cnt} edges from {source_node.event.base_id} to next cycle by passby in prev day")
                all_build_num += cnt
            # 2. 考虑后一执勤日开始时置位
            for source_node_id in node_ids:
                source_node = node_id_2_node[source_node_id]
                if source_node.destination not in crew_possible_bases:
                    continue
                time_arrived_nxt_airport_by_bus: Dict[str, Tuple[datetime.datetime, str]] = defaultdict(lambda: (datetime.datetime.max, ""))
                time_arrived_nxt_airport_by_flight: Dict[str, Dict[str, Tuple[datetime.datetime, str]]] = defaultdict(lambda: defaultdict(lambda: (datetime.datetime.max, "")))
                new_airport_set: Set[str] = set()
                ed = source_node.end_day
                # 2.1 考虑大巴置位
                if destination in bus_source_2_node_ids:
                    idx = bisect.bisect_left(bus_source_2_node_ids[destination], ed + CYCLE_DAY_GAP, key=lambda x: bus_id_2_bus[x].st.toordinal())
                    for bus_id in bus_source_2_node_ids[destination][idx:]:
                        bus = bus_id_2_bus[bus_id]
                        if (bus.st.toordinal() - source_node.end_day) > CYCLE_WAIT_DAY_MAX_GAP:
                            break
                        new_airport_set.add(bus.destination)
                        if time_arrived_nxt_airport_by_bus[bus.destination][0] > bus.et:
                            time_arrived_nxt_airport_by_bus[bus.destination] = (bus.et, bus_id)
                # 2.2 考虑航班置位
                if destination in flight_source_2_node_ids:
                    idx = bisect.bisect_left(flight_source_2_node_ids[destination], ed + CYCLE_DAY_GAP, key=lambda x: node_id_2_node[x].start_day)
                    for flight_id in flight_source_2_node_ids[destination][idx:]:
                        flight = node_id_2_node[flight_id]
                        if not isinstance(flight.event, Flight):
                            continue
                        aircraft = flight.event.aircraftNo
                        if CYCLE_WAIT_DAY_MAX_GAP >= (flight.start_day - ed):
                            new_airport_set.add(flight.destination)
                            if time_arrived_nxt_airport_by_flight[flight.destination][aircraft][0] > flight.et:
                                time_arrived_nxt_airport_by_flight[flight.destination][aircraft] = (flight.et, flight_id)
                        else:
                            break
                # print("source_node: " + source_node.event.base_id + " can go to " + str(len(new_airport_set)) + " airports by passby in next day")
                cnt = 0
                # 2.3 更新到达每个机场的几个时间指标，优化时间复杂度
                # 这个字典是所有passby方式到达，假设都需要等待才能开始下阶段任务的最小时间
                # 具体使用需要再去查同飞机型号的是否存在，存在则不罚时取min
                really_can_start_time_map: Dict[str, Tuple[datetime.datetime, str]] = defaultdict(lambda: (datetime.datetime.max, ""))
                min_time_arrived_map: Dict[str, Tuple[datetime.datetime, str]] = defaultdict(lambda: (datetime.datetime.max, ""))
                for new_airport in new_airport_set:
                    min_time_arrived = (datetime.datetime.max, "")
                    if new_airport in time_arrived_nxt_airport_by_bus:
                        min_time_arrived = min(min_time_arrived, time_arrived_nxt_airport_by_bus[new_airport])
                        if really_can_start_time_map[new_airport][0] > time_arrived_nxt_airport_by_bus[new_airport][0] + datetime.timedelta(seconds=WAITING_TIME_BETWEENT_BUS_AND_FLIGHT):
                            really_can_start_time_map[new_airport] = (time_arrived_nxt_airport_by_bus[new_airport][0] + datetime.timedelta(seconds=WAITING_TIME_BETWEENT_BUS_AND_FLIGHT), time_arrived_nxt_airport_by_bus[new_airport][1])
                    if new_airport in time_arrived_nxt_airport_by_flight:
                        for aircraft, time_arrived_by_aircraft in time_arrived_nxt_airport_by_flight[new_airport].items():
                            min_time_arrived = min(min_time_arrived, time_arrived_by_aircraft)
                            if really_can_start_time_map[new_airport][0] > time_arrived_by_aircraft[0] + datetime.timedelta(seconds=WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT):
                                really_can_start_time_map[new_airport] = (time_arrived_by_aircraft[0] + datetime.timedelta(seconds=WAITING_TIME_BETWEEN_DIFFERENT_AIRCRAFT), time_arrived_by_aircraft[1])
                    min_time_arrived_map[new_airport] = min_time_arrived
                # 2.4 对每个新机场，找到可以创建的边
                for new_airport, time_arrived in min_time_arrived_map.items():
                    if new_airport not in event_source_2_node_ids:
                        continue
                    idx = bisect.bisect_left(event_source_2_node_ids[new_airport], time_arrived[0], key=lambda x: node_id_2_node[x].st)
                    for destination_node_id in event_source_2_node_ids[new_airport][idx:]:
                        destination_node = node_id_2_node[destination_node_id]
                        really_can_start_time = really_can_start_time_map[new_airport][0]
                        passby_event = really_can_start_time_map[new_airport][1]
                        if isinstance(destination_node.event, Flight):
                            nxt_aircraft = destination_node.event.aircraftNo
                        
                            if really_can_start_time > time_arrived_nxt_airport_by_flight[new_airport][nxt_aircraft][0]:
                                really_can_start_time = time_arrived_nxt_airport_by_flight[new_airport][nxt_aircraft][0]
                                passby_event = time_arrived_nxt_airport_by_flight[new_airport][nxt_aircraft][1]
                        else:
                            really_can_start_time = time_arrived[0]
                            passby_event = time_arrived[1]
                        if destination_node.st < really_can_start_time:
                            continue
                        if destination_node.st > really_can_start_time + datetime.timedelta(seconds=WAITING_TIME_LIMIT):
                            break
                        edge_type = EdgeType.EDGE_TO_NEXT_DUTY_DAY
                        edge = Edge(source_node, destination_node, edge_type)
                        event_id = passby_event
                        prefix = passby_event.split("_")[0]
                        tmp = flight_id_2_flight[event_id] if prefix == "Flt" else bus_id_2_bus[event_id]
                        edge.passby_event.append(tmp)
                        edge.penalty_of_deadhead = len(edge.passby_event) * LEGAL_DEADHEAD_COST
                        source_node.out_edges.append(edge)
                        destination_node.in_edges.append(edge)
                        cnt += 1
                        # print(f"Build edge {edge} with passby event {edge.passby_event}")
                # print(f"Build {cnt} edges from {source_node.event.base_id} to next cycle by passby in next day")
                all_build_num += cnt
        print(f"Total {all_build_num} edges built with deadhead in next cycle")
                        
    build_edge_in_same_base()
    build_edge_with_deadhead()


def build_event_graph(
    flights: List[Flight],
    grounds: List[GroundDuty]
):
    # 1. build nodes
    for flight in flights:
        node_id = flight.base_id
        flight_node_id_2_node[node_id] = Node(flight)
        node_id_2_node[node_id] = flight_node_id_2_node[node_id]
        event_destination_2_node_ids[flight.destination].append(node_id)
        event_source_2_node_ids[flight.source].append(node_id)
        flight_destination_2_node_ids[flight.destination].append(node_id)
        flight_source_2_node_ids[flight.source].append(node_id)
    for ground in grounds:
        node_id = ground.base_id
        ground_duty_node_id_2_node[node_id] = Node(ground)
        node_id_2_node[node_id] = ground_duty_node_id_2_node[node_id]
        event_destination_2_node_ids[ground.destination].append(node_id)
        event_source_2_node_ids[ground.source].append(node_id)
    for des, lst in event_destination_2_node_ids.items():
        lst.sort(key=lambda x: node_id_2_node[x].et)
    for source, lst in event_source_2_node_ids.items():
        lst.sort(key=lambda x: node_id_2_node[x].st)
    for bus in bus_id_2_bus.values():
        node_id = bus.base_id
        bus_source_2_node_ids[bus.source].append(node_id)
        bus_destination_2_node_ids[bus.destination].append(node_id)
    for des, lst in bus_destination_2_node_ids.items():
        lst.sort(key=lambda x: bus_id_2_bus[x].et)
    for source, lst in bus_source_2_node_ids.items():
        lst.sort(key=lambda x: bus_id_2_bus[x].st)
    for des, lst in flight_destination_2_node_ids.items():
        lst.sort(key=lambda x: node_id_2_node[x].et)
    for source, lst in flight_source_2_node_ids.items():
        lst.sort(key=lambda x: node_id_2_node[x].st)
    
    # 2. build edges
    # 2.1 try to find EDGE_IN_SAME_DUTY_DAY, which edge.source_node.destination == edge.destination_node.source && edge.destination_node.st >= edge.source_node.et && (edge.destination_node.st - edge.source_node.et) <= WAITING_TIME_LIMIT
    build_edge_in_the_same_duty_day()
    # 2.2 try to find EDGE_TO_NEXT_DUTY_DAY
    build_edge_to_next_duty_day()
    # 2.3 try to find EDGE_OVER_FLIGHT_CYCLE
    build_edge_to_next_cycle()
    # todo build illegal edges, which are edges that are not allowed by the rules
    return


# Example of usage after loading your data:
if __name__ == "__main__":
    flights = list(flight_id_2_flight.values())
    grounds = list(ground_id_2_ground.values())
    build_event_graph(flights, grounds)
    # Now `graph` maps e.g. "Flt_10" → ["grd_5", "Flt_20", ...] depending on matches.
    # You can inspect:


