from typing import Set, Dict, Tuple
from read_data import crew_id_2_crew, flight_id_2_flight, bus_id_2_bus, ground_id_2_ground
from build_graph 



class Params:
    """
    crew_idx_set	Set	机组人员节点的索引集合
    flight_idx_set	Set	飞行任务节点的索引集合
    other_duty_idx_set	Set	其他任务（非飞行）节点的索引集合
    allocation_arc_set	Set of Tuples	需要置位的弧集合（格式：(i,j)）
    all_in	Dict[Node: Set]	每个节点的入边邻居字典（格式：{节点: 前驱节点集合}）
    all_out	Dict[Node: Set]	每个节点的出边邻居字典（格式：{节点: 后继节点集合}）
    max_flight_num	int	单个执勤日内允许的最大飞行任务数量
    max_tot_duty_num	int	单个执勤日内允许的最大任务总量（飞行+其他）
    flight_time	Dict[Task: float]	每个飞行任务的持续时间
    max_flight_time_within_duty_day	float	执勤日内允许的最大总飞行时间
    rest_out	Dict[Node_id: Set]	每个节点后可连接的休息节点集合,>=24h
    Rest_out	Dict[Node_id: Set]	每个节点后可连接的休息节点集合,>=2days（两个完整日历日）
    max_work_day	int	单个执勤周期允许的最大连续工作天数
    p	Dict[(i,j): float]	从任务i到j的时间/天数的传递增量
    q	Dict[(k,i): float]	机组人员k在任务i后可以休息，由base判断
    max_flight_time	float	单个机组人员总飞行时间上限
    crew2flight	Dict[Crew: Set]	机组人员可执行的任务映射（格式：{机组: 可执行任务集合}）
    flight2crew	Dict[Flight: Set]	任务（包括飞行和其他任务）可分配的机组映射（格式：{任务: 可执行机组集合}）
    """
    def __init__(self):
        self.crew_idx_set: Set[str] = set(crew_id_2_crew.keys())
        self.flight_idx_set: Set[str] = set(flight_id_2_flight.keys())
        self.other_duty_idx_set: Set[str] = set(bus_id_2_bus.keys()) | set(ground_id_2_ground.keys())
        self.allocation_arc_set: Set[Tuple[str, str]] = set()
        self.all_in: Dict[str, Set[str]] = {}
        self.all_out: Dict[str, Set[str]] = {}
        self.max_flight_num: int = 5
        self.max_tot_duty_num: int = 10
        self.flight_time: Dict[str, float] = {flight_id: flight.fly_time for flight_id, flight in flight_id_2_flight.items()}
        self.max_flight_time_within_duty_day: float = 8.0
        self.rest_out: Dict[str, Set[str]] = {}
        self.Rest_out: Dict[str, Set[str]] = {}
        self.max_work_day: int = 7
        self.p: Dict[Tuple[str, str], float] = {}
        self.q: Dict[Tuple[str, str], float] = {}
        self.max_flight_time: float = 100.0
        self.crew2flight: Dict[str, Set[str]] = {crew_id: crew.eligible_flights for crew_id, crew in crew_id_2_crew.items()}
        self.flight2crew: Dict[str, Set[str]] = {flight_id: flight_2_matched_crews for flight_id, flight_2_matched_crews in flight_id_2_flight.items()}