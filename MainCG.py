from gurobipy import *


class cg_crew_scheduling:
    def __init__(self):
        self.col_id2col = dict()
        self.col2col_id = dict()
        self.model_id2col_id = dict()
        self.model = Model("crew_scheduling")
        self.shadow_price = []
        self.max_col_num_per_sp = 500
        self.col_cnt = dict()

    def get_initial_columns(self):
        pass
    def _solve(self):
        # solve and get
        pass

    def _solve_integer(self):
        pass

    def sub_problem(self):
        pass

    def add_columns(self, col_set, model_id):
        for crew_id, cost, column in col_set:
            if crew_id not in self.col_cnt:
                self.col_cnt[crew_id] = 0
            cols = self.model.getConstrs()
            col_coeff = [0 for _ in range(len(cols))]
            for j in column:
                col_coeff[j] = 1
            temp_col = Column(col_coeff, cols)
            self.model.addVar(obj=cost, vtype='B', column=temp_col)
            self.col_id2col[crew_id, self.col_cnt[crew_id]] = column
            self.col2col_id[column].add((crew_id, self.col_cnt[crew_id]))
            self.model_id2col_id[model_id].add((crew_id, self.col_cnt[crew_id]))
            self.col_cnt[crew_id] += 1

    def update_dual(self):
        self.shadow_price = self.model.getAttr(GRB.Attr.Pi, self.model.getConstrs())

    def fix_col(self):
        pass

    def check_termination(self):
        pass

    def main(self):
        max_iter_num = 10
        model_id = 0
        while 1:
            for _ in range(max_iter_num):
                self._solve()
                columns = self.sub_problem()
                if len(columns) == 0: break
                self.add_columns(columns, model_id)
            self._solve_integer()
            self.fix_col()
            if self.check_termination():
                break



