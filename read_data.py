from collections import defaultdict, deque
from typing import List, Dict, Set, Sequence, ClassVar
import json
import time
import re
from dataclasses import field, dataclass
import datetime

import pandas as pd
import bisect


@dataclass
class Crew(object):
    base: str
    stay_station: str
    crew_id: str
    id_prefix: str = "Crew_"
    # eligible_flights: Set[int] = field(default_factory=set)


@dataclass
class Event(object):
    base_id: str
    source: str
    destination: str
    st: datetime.datetime
    et: datetime.datetime
    id_prefix: ClassVar[str] = "Event_"

    def __lt__(self, other):
        if self.st == other.st:
            return self.et < other.et
        return self.st < other.st


@dataclass
class Flight(Event):
    fleet: str
    aircraftNo: str
    flyTime: int
    id_prefix: ClassVar[str] = "Flt_"


@dataclass
class GroundDuty(Event):
    crew_id: int
    is_duty: int
    id_prefix: ClassVar[str] = "grd_"


@dataclass
class BusTravel(Event):
    id_prefix: ClassVar[str] = "ddh_"


event_set = {"bus": BusTravel, "flight": Flight, "ground": GroundDuty}

flight_id_2_flight: Dict[str, Flight] = {}
crew_2_matched_flights: Dict[str, Set[str]] = defaultdict(set)
flight_2_matched_crews: Dict[str, Set[str]] = defaultdict(set)
crew_id_2_crew: Dict[str, Crew] = {}
layover_bases: Set[str] = set()
ground_id_2_ground: Dict[str, GroundDuty] = {}
bus_id_2_bus: Dict[str, BusTravel] = {}
crew_possible_bases: Set[str] = set()

# read data code, but commented out to avoid running it if unnecessary
flight_data = pd.read_csv("data/flight.csv")
for index, row in flight_data.iterrows():
    base_id = row['id']
    # base_id = int(base_id.split("_")[1])
    source = row['depaAirport']
    destination = row['arriAirport']
    st = pd.to_datetime(row['std'])
    et = pd.to_datetime(row['sta'])
    fleet = row['fleet']
    aircraftNo = row['aircraftNo']
    flyTime = row['flyTime']
    flight_obj = Flight(base_id, source, destination, st, et, fleet, aircraftNo, flyTime)
    flight_id_2_flight[base_id] = flight_obj
crew_data = pd.read_csv("data/crew.csv")
# crew_match_data = pd.read_csv("data/crewLegMatch.csv")
# print(crew_match_data.size)
# for index, row in crew_match_data.iterrows():
#     crew_id = int(row['crewId'].split("_")[1])
#     ground_id = int(row['legId'].split("_")[1])
#     if ground_id not in flight_id_2_flight:
#         print(ground_id, " not in flight_id_2_flight")
#     crew_2_matched_flights[crew_id].add(ground_id)
#     flight_2_matched_crews[ground_id].add(crew_id)
for index, row in crew_data.iterrows():
    crew_id = row['crewId']
    # crew_id = int(row['crewId'].split("_")[1])
    base = row['base']
    stay_station = row['stayStation']
    crew_obj = Crew(base, stay_station, crew_id)
    # if crew_id not in crew_2_matched_flights:
    #     print(crew_id, " not in crew_2_matched_flights")
    # crew_obj.eligible_flights = crew_2_matched_flights[crew_id]
    crew_id_2_crew[crew_id] = crew_obj
    crew_possible_bases.add(base)
    # crew_obj.id_prefix = row['crewId'].split("_")[0] + "_"
layover_data = pd.read_csv("data/layoverStation.csv")
for index, row in layover_data.iterrows():
    layover_bases.add(row['airport'])
ground_data = pd.read_csv("data/groundDuty.csv")
for index, row in ground_data.iterrows():
    # base_id = int(row['id'].split("_")[1])
    base_id = row['id']
    source = row['airport']
    destination = row['airport']
    st = pd.to_datetime(row['startTime'])
    et = pd.to_datetime(row['endTime'])
    # crew_id = int(row['crewId'].split("_")[1])
    crew_id = row['crewId']
    is_duty = int(row['isDuty'])
    ground_obj = GroundDuty(base_id, source, destination, st, et, crew_id, is_duty)
    ground_id_2_ground[base_id] = ground_obj
# print(ground_id_2_ground)
# print(len(ground_id_2_ground))
bus_data = pd.read_csv("data/busInfo.csv")
for index, row in bus_data.iterrows():
    # bus_id = int(row['id'].split("_")[1])
    bus_id = row['id']
    source = row['depaAirport']
    destination = row['arriAirport']
    st = pd.to_datetime(row['td'])
    et = pd.to_datetime(row['ta'])
    bus_obj = BusTravel(bus_id, source, destination, st, et)
    bus_id_2_bus[bus_id] = bus_obj
# print(bus_id_2_bus)
# print(len(bus_id_2_bus))


start_time_order_event_list: List[Event] = []
start_time_order_flight_list: List[Flight] = []
start_time_order_bus_list: List[BusTravel] = []
start_time_order_ground_list: List[GroundDuty] = []
for flight in flight_id_2_flight.values():
    start_time_order_event_list.append(flight)
    start_time_order_flight_list.append(flight)
for ground in ground_id_2_ground.values():
    start_time_order_event_list.append(ground)
    start_time_order_ground_list.append(ground)
for bus in bus_id_2_bus.values():
    start_time_order_event_list.append(bus)
    start_time_order_bus_list.append(bus)
start_time_order_event_list.sort(key=lambda x: (x.st, x.et))
start_time_order_flight_list.sort(key=lambda x: (x.st, x.et))
start_time_order_bus_list.sort(key=lambda x: (x.st, x.et))
start_time_order_ground_list.sort(key=lambda x: (x.st, x.et))
# print(start_time_order_event_list)


def get_time_range_events(start_time: datetime.datetime, end_time: datetime.datetime, event_type: str = "event") -> \
        Sequence[Event]:
    """
    Get all events within the specified time range.
    """
    target, lf, rf = [], Event("0", "", "", start_time, start_time), Event("0", "", "", end_time, end_time)
    if event_type == "flight":
        target = start_time_order_flight_list
        lf = Flight("0", "", "", start_time, start_time, "", "", 0)
        rf = Flight("0", "", "", end_time, end_time, "", "", 0)
    elif event_type == "ground":
        target = start_time_order_ground_list
        lf = GroundDuty("0", "", "", start_time, start_time, 0, 0)
        rf = GroundDuty("0", "", "", end_time, end_time, 0, 0)
    elif event_type == "bus":
        target = start_time_order_bus_list
        lf = BusTravel("0", "", "", start_time, start_time)
        rf = BusTravel("0", "", "", end_time, end_time)
    else:
        target = start_time_order_event_list
    left_index = bisect.bisect_left(target, lf)
    right_index = bisect.bisect_right(target, rf)
    return target[left_index:right_index]


if __name__ == "__main__":
    temp = get_time_range_events(datetime.datetime(2025, 5, 29, 11, 0, 0),
                                 datetime.datetime(2025, 5, 29, 23, 0, 0),
                                 "flight")
    for crew in crew_id_2_crew.values():
        for ground in ground_id_2_ground.values():
            if crew.crew_id == ground.crew_id:
                if crew.base != ground.source:
                    print(crew.crew_id, "'s base " + crew.base + " is not same with " + ground.base_id + "'s source " + ground.source)
    onduty = 0
    for ground in ground_id_2_ground.values():
        if ground.is_duty == 1:
            onduty += 1
    print("Total number of ground duties:", len(ground_id_2_ground))
    print("Total number of onduty ground duties:", onduty)
    for crew in crew_id_2_crew.values():
        if crew.base not in layover_bases:
            print(crew.crew_id, "base", crew.stay_station, "is not in layover bases")
        if crew.stay_station not in layover_bases:
            print(crew.crew_id, "stay station", crew.stay_station, "is not in layover bases")
    # print(temp)
