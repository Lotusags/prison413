from gurobipy import *

class crew_schedule_generator:
    def __init__(self, params):
        ## 注意，虚拟的起点为0
        self.params = params # 用于传递所有需要的参数
        self.model = Model("crew_scheduling")
        self.x = {} # xij，表示弧是否被选择
        self.y = {} # yi,i后是否休息，用于结束执勤日
        self.z = {} # 节点i后的飞行任务数量
        self.tot_z = {} # 节点i后的任务数量
        self.w = {} # i执行完后的飞行时长
        self.v = {} # vij，机组人员i是否执行航班j
        self.u = {} # uij，ij是否由同一个人访问
        self.r = {} # i后的节点是否休息，用于结束飞行周期
        self.workday = {} # 节点i后执勤周期的天数
        self.aux = {} # 任务i是否被执行
        self.S = 1e6 # 一个大常数

    def _add_objective(self):
        obj = LinExpr()
        for var in self.u.values():
            obj.addTerms([self.S], var)

        for var in self.u.values():
            obj.addTerms([self.S], var)

        for var in self.aux.values():
            obj.addTerms([self.S], var)

        self.model.setObjective(obj)

    def _initial_variables(self):
        for i in self.params.crew_idx_set:
            self.x[0, i] = self.model.addVar(vtype=GRB.BINARY, name="x" + str(0) + ',' + str(i))

        for i in self.params.crew_idx_set:
            for j in self.params.crew2flight[i]:
                self.x[i, j] = self.model.addVar(vtype=GRB.BINARY, name="x" + str(i) + ',' + str(j))
                self.v[i, j] = self.model.addVar(vtype=GRB.BINARY, name="v" + str(i) + ',' + str(j))
            for j in self.params.other_duty_idx_set:
                self.x[i, j] = self.model.addVar(vtype=GRB.BINARY, name="x" + str(i) + ',' + str(j))
                self.v[i, j] = self.model.addVar(vtype=GRB.BINARY, name="v" + str(i) + ',' + str(j))

        for i in (self.params.flight_idx_set | self.params.other_duty_idx_set):
            self.x[i, 0] = self.model.addVar(vtype=GRB.BINARY, name="x" + str(i) + ',' + str(0))
            for j in (self.params.flight_idx_set | self.params.other_duty_idx_set):
                self.x[i, j] = self.model.addVar(vtype=GRB.BINARY, name="x" + str(i) + ',' + str(j))
                self.u[i, j] = self.model.addVar(vtype=GRB.CONTINUOUS, name="u" + str(i) + ',' + str(j))

        for i in self.params.flight_idx_set:
            self.y[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="y" + str(i))
            self.z[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="z" + str(i))
            self.tot_z[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="tot_z" + str(i))
            self.w[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="w" + str(i))
            self.r[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="r" + str(i))
            self.workday[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="workday" + str(i))
            self.aux[i] = self.model.addVar(vtype=GRB.BINARY, name="aux" + str(i))

        for i in self.params.other_duty_idx_set:
            self.y[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="y" + str(i))
            self.z[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="z" + str(i))
            self.tot_z[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="tot_z" + str(i))
            self.w[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="w" + str(i))
            self.r[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="r" + str(i))
            self.workday[i] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="workday" + str(i))
            self.aux[i] = self.model.addVar(vtype=GRB.BINARY, name="aux" + str(i))

    def _add_constrains(self):
        pass

    def _add_link_constraints(self):
        all_set = self.params.flight_idx_set | self.params.crew_idx_set | self.params.other_duty_idx_set
        for i in all_set:
            in_value = LinExpr()
            for j in self.params.all_in[i]:
                in_value.addTerms(1, self.x[j, i])
            out_value = LinExpr()
            for j in self.params.all_out[i]:
                out_value.addTerms(1, self.x[i, j])
            self.model.addConstr(in_value == out_value, name="Link Constraint" + str(i))


    def _add_flight_exe_constrains(self):
        for i in self.params.flight_idx_set:
            temp = LinExpr()
            for j in self.params.all_out[i]:
                temp.addTerms(1, self.x[i, j])
            self.model.addConstr(temp == 1 - self.aux[i], name="Flight Execution penalty" + str(i))

        for i in self.params.other_duty_idx_set:
            temp = LinExpr()
            for j in self.params.all_out[i]:
                temp.addTerms(1, self.x[i, j])
            self.model.addConstr(temp == 1 - self.aux[i], name="Other Duty Execution penalty" + str(i))

    def _add_replace_constrains(self):
        for i, j in self.params.allocation_arc_set:
            self.model.addConstr(self.x[i, j] <= self.y[i] + self.y[j], name="Allocation Constraint" + str(i) + ',' + str(j))

    def _add_duty_place_connection_constrains(self):
        pass

    def _add_max_duty_num_constraints(self):
        for i in self.params.flight_idx_set:
            for j in self.params.all_out[i]:
                self.model.addConstr(self.z[j] >= self.z[i] + 1 - self.S*(1 - self.x[i, j] - self.y[i]))
                self.model.addConstr(self.tot_z[j] >= self.tot_z[i] + 1 - self.S * (1 - self.x[i, j] - self.y[i]))
            self.model.addConstr(self.z[i] <= self.params.max_flight_num)
            self.model.addConstr(self.tot_z[i] <= self.params.max_tot_duty_num)

        for i in self.params.other_duty_idx_set:
            for j in self.params.all_out[i]:
                self.model.addConstr(self.tot_z[j] >= self.tot_z[i] + 1 - self.S * (1 - self.x[i, j] - self.y[i]))
                self.model.addConstr(self.z[j] >= self.z[i] - self.S*(1 - self.x[i, j] - self.y[i]))
            self.model.addConstr(self.tot_z[i] <= self.params.max_tot_duty_num)

    def _add_max_fly_time_dutyday_constraints(self):
        for i in self.params.flight_idx_set:
            for j in self.params.all_out[i]:
                self.model.addConstr(self.w[j] >= self.w[i] + self.params.flight_time[i] - self.S * (1 - self.x[i, j] - self.y[i]))
            self.model.addConstr(self.w[i] <= self.params.max_flight_time_within_duty_day)

    def _add_min_resttime_before_dutyday_constraints(self):
        for i in self.params.flight_idx_set | self.params.other_duty_idx_set:
            for j in self.params.rest_out[i]:
                self.model.addConstr(self.x[i, j] <= self.y[i])

    def _add_min_resttime_within_fly_period_constraints(self):
        for i in self.params.flight_idx_set | self.params.other_duty_idx_set:
            for j in self.params.all_out[i]:
                self.model.addConstr(self.workday[j] >= self.workday[i] + self.params.p[i, j] - self.S*(1 - self.x[i, j] - self.r[i]))
                part1 = LinExpr()
                for j in self.params.Rest_out[i]:
                    part1.addTerms(1, self.x[i, j])
                part2 = LinExpr()
                for k in self.params.crew_idx_set:
                    part2.addTerms(1, self.v[k, i]*self.q[k, i])
                self.model.addConstr(self.r[i] <= part2 + part1)
            self.model.addConstr(self.workday[i] <= self.params.max_work_day)

    def _add_max_tot_duty_time_constraints(self):
        temp_sum = LinExpr()
        for k in self.params.crew_idx_set:
            for i in self.params.flight_idx_set:
                temp_sum.addTerms(self.params.flight_time, self.v[k, i])
            self.model.addConstr(temp_sum <= self.params.max_flight_time)

    def _add_qualification_constraints(self):

        for j in self.params.flight_idx_set:
            temp = LinExpr()
            for i in self.params.flight2crew[j]:
                temp.addTerms(1, self.v[i, j])
            self.model.addConstr(temp + self.aux[j] == 1)

        for i in self.params.crew_idx_set:
            for j in self.params.crew_idx_set:
                temp = self.params.crew2flight[i] & self.params.crew2flight[j]
                if i == j or len(temp) == 0:
                    continue
                temp_sum = LinExpr()
                for k in temp:
                    temp_sum.addTerms(1, self.v[k, i] + self.v[k, j])
                self.model.addConstr(self.u[i, j] >= temp_sum - 1)

        for i in self.params.crew_idx_set:
            for j in self.params.crew2flight:
                self.model.addConstr(self.x[i, j] <= self.v[i, j])

        for i in self.params.flight_idx_set | self.params.other_duty_idx_set:
            for j in self.params.flight_idx_set | self.params.other_duty_idx_set:
                if i != j:
                    self.model.addConstr(self.x[i, j] == self.u[i, j])

    def _process_solution(self):
        res = []
        return res

    def solve(self):
        self._initial_variables()
        self._add_objective()
        self._add_constrains()
        res = self._process_solution()
        return res
