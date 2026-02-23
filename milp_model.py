
import pulp

class TacticalAssemblyLineFeedingModel:
    def __init__(self, sets, params):
        """
        Initializes the MILP model.
        """
        self.sets = sets
        self.params = params
        self.prob = pulp.LpProblem("TacticalAssemblyLineFeeding", pulp.LpMinimize)

        # Unpack sets
        self.V = sets['V']
        self.W = sets['W']
        self.I = sets['I']
        self.F = sets['F']
        self.C = sets['C']
        self.P = sets['P'] # ['LS', 'BS', 'Seq', 'SK', 'TK']
        self.I_f = sets['I_f']
        self.I_w = sets['I_w']
        self.F_w = sets['F_w']

        # Decision Variables
        self.PX = pulp.LpVariable.dicts("PX", ((i, p) for i in self.I for p in self.P), cat='Binary')
        self.PY = pulp.LpVariable.dicts("PY", ((i, c) for i in self.I for c in self.C), cat='Binary')
        self.PCF = pulp.LpVariable.dicts("PCF", ((i, p, c, v) for i in self.I for p in self.P for c in self.C for v in self.V), cat='Binary')
        self.PLF = pulp.LpVariable.dicts("PLF", ((i, p, c, v) for i in self.I for p in self.P for c in self.C for v in self.V), cat='Binary')

        # Auxiliary Variables
        self.X_F = pulp.LpVariable.dicts("X_F", ((f, p) for f in self.F for p in self.P), cat='Binary')
        self.Y_F = pulp.LpVariable.dicts("Y_F", ((f, c) for f in self.F for c in self.C), cat='Binary')
        self.X_K = pulp.LpVariable.dicts("X_K", (w for w in self.W), cat='Binary')
        self.Z = pulp.LpVariable.dicts("Z", ((c, p) for c in self.C for p in self.P), cat='Binary')
        self.TLF = pulp.LpVariable.dicts("TLF", ((c, v) for c in self.C for v in self.V), cat='Binary')
        self.KLF = pulp.LpVariable.dicts("KLF", ((w, c, v) for w in self.W for c in self.C for v in self.V), cat='Binary')

        # BS Racks (linearized)
        self.bsracks = pulp.LpVariable.dicts("bsracks", (w for w in self.W), lowBound=0, cat='Integer')

    def build_model(self):
        # Objective Function
        obj = 0

        # Replenishment Cost
        for i in self.I:
            for p in self.P:
                for c in self.C:
                    for v in self.V:
                        cost = self.params['C_ipcv_Re'].get((i,p,c,v), 0)
                        if cost > 0: obj += cost * self.PCF[i,p,c,v]

        # Preparation Cost
        for i in self.I:
            for p in self.P:
                for c in self.C:
                     cost = self.params['C_ipc_P'].get((i,p,c), 0)
                     if cost > 0:
                         term = pulp.lpSum(self.PCF[i,p,c,v] for v in self.V)
                         obj += cost * term

        # Transportation Cost (Parts)
        for i in self.I:
            for p in self.P:
                for c in self.C:
                    for v in self.V:
                        cost = self.params['C_ipcv_T'].get((i,p,c,v), 0)
                        if cost > 0: obj += cost * self.PLF[i,p,c,v]

        # Transportation Cost (Kits to Workstation)
        for w in self.W:
            for c in self.C:
                for v in self.V:
                    cost = self.params['C_wcv_T'].get((w,c,v), 0)
                    if cost > 0: obj += cost * self.KLF[w,c,v]

        # Transportation Cost (Travelling Kits)
        for c in self.C:
            for v in self.V:
                cost = self.params['C_cv_T'].get((c,v), 0)
                if cost > 0: obj += cost * self.TLF[c,v]

        # Usage Cost
        for i in self.I:
            for p in self.P:
                cost = self.params['C_ip_U'].get((i,p), 0)
                if cost > 0: obj += cost * self.PX[i,p]

        self.prob += obj

        # Constraints
        M = self.params['M']

        # (1.1) Sum PX_ip = 1
        for i in self.I:
            self.prob += pulp.lpSum(self.PX[i,p] for p in self.P) == 1

        # (1.2) Sum PY_ic = Sum PX_ip (p != LS)
        P_no_LS = [p for p in self.P if p != 'LS']
        for i in self.I:
            self.prob += pulp.lpSum(self.PY[i,c] for c in self.C) == pulp.lpSum(self.PX[i,p] for p in P_no_LS)

        # (1.3) Z_cp >= PX_ip + PY_ic - 1
        for i in self.I:
            for c in self.C:
                for p in self.P:
                    self.prob += self.Z[c,p] >= self.PX[i,p] + self.PY[i,c] - 1

        # (1.4) Sum Z_cp <= 1
        for c in self.C:
            self.prob += pulp.lpSum(self.Z[c,p] for p in self.P) <= 1

        # (1.5) Sum Z_cp <= Sum PY_ic
        for c in self.C:
            self.prob += pulp.lpSum(self.Z[c,p] for p in self.P) <= pulp.lpSum(self.PY[i,c] for i in self.I)

        # (1.6) PX_ip = X_fp_F
        for f in self.F:
            for i in self.I_f[f]:
                for p in self.P:
                    self.prob += self.PX[i,p] == self.X_F[f,p]

        # (1.7) PY_ic >= Y_fc_F
        for f in self.F:
            for i in self.I_f[f]:
                for c in self.C:
                    self.prob += self.PY[i,c] >= self.Y_F[f,c]

        # (1.8) Sum Y_fc_F = Sum X_fp_F (p != LS, BS)
        P_no_LS_BS = [p for p in self.P if p not in ['LS', 'BS']]
        for f in self.F:
            self.prob += pulp.lpSum(self.Y_F[f,c] for c in self.C) == pulp.lpSum(self.X_F[f,p] for p in P_no_LS_BS)

        # (1.10) Sum Y_fc_F <= 1 + M(Z_c_SK + Z_c_TK)
        for c in self.C:
            term = 0
            if 'SK' in self.P: term += self.Z[c,'SK']
            if 'TK' in self.P: term += self.Z[c,'TK']
            self.prob += pulp.lpSum(self.Y_F[f,c] for f in self.F) <= 1 + M * term

        # (1.11) Cell Capacity
        for c in self.C:
            for p in self.P:
                self.prob += pulp.lpSum(self.PY[i,c] for i in self.I) * self.params['k_p_P'][p] <= self.params['k_c_C'][c] + M * (1 - self.Z[c,p])

        # (1.12) Workstation Capacity (w != 1)
        for w in self.W:
            if w == 1: continue
            lhs = 0
            if 'LS' in self.P:
                for f in self.F_w.get(w, []):
                    lhs += self.X_F[f,'LS'] * self.params['k_p_P']['LS'] * len(self.I_f[f])
            if 'BS' in self.P:
                lhs += self.bsracks[w] * self.params['k_p_P']['BS']
            if 'Seq' in self.P:
                for f in self.F_w.get(w, []):
                     lhs += self.X_F[f,'Seq'] * self.params['k_p_P']['Seq']
            lhs += self.X_K[w] * self.params['K_KP']
            self.prob += lhs <= self.params['k_w_W'][w]

        # (1.13) Workstation 1 Capacity
        if 1 in self.W:
            w = 1
            lhs = 0
            if 'LS' in self.P:
                for f in self.F_w.get(w, []):
                    lhs += self.X_F[f,'LS'] * self.params['k_p_P']['LS'] * len(self.I_f[f])
            if 'BS' in self.P:
                lhs += self.bsracks[w] * self.params['k_p_P']['BS']
            if 'Seq' in self.P:
                for f in self.F_w.get(w, []):
                     lhs += self.X_F[f,'Seq'] * self.params['k_p_P']['Seq']
            lhs += self.X_K[w] * self.params['K_KP']
            if 'TK' in self.P:
                lhs += pulp.lpSum(self.Z[c,'TK'] for c in self.C) * self.params['k_p_P']['TK']
            self.prob += lhs <= self.params['k_w_W'][w]

        # (1.14) X_w_K definition
        for w in self.W:
            self.prob += self.X_K[w] == pulp.lpSum(self.KLF[w,c,v] for c in self.C for v in self.V)

        # (1.15) Kit Volume
        if 'TK' in self.P:
            self.prob += pulp.lpSum(self.params['k_f_FV'][f] * self.X_F[f,'TK'] for f in self.F) <= self.params['K_KV']

        # (1.16) Kit Weight
        if 'TK' in self.P:
            self.prob += pulp.lpSum(self.params['k_f_FW'][f] * self.X_F[f,'TK'] for f in self.F) <= self.params['K_KW']

        # (1.17) SK Volume
        if 'SK' in self.P:
            for w in self.W:
                for c in self.C:
                    lhs = pulp.lpSum(self.params['k_f_FV'][f] * self.Y_F[f,c] for f in self.F_w.get(w, []))
                    self.prob += lhs <= self.params['K_KV'] + M * (1 - self.Z[c,'SK'])

        # (1.18) SK Weight
        if 'SK' in self.P:
            for w in self.W:
                for c in self.C:
                    lhs = pulp.lpSum(self.params['k_f_FW'][f] * self.Y_F[f,c] for f in self.F_w.get(w, []))
                    self.prob += lhs <= self.params['K_KW'] + M * (1 - self.Z[c,'SK'])

        # (1.19) Replenishment Req
        P_no_LS = [p for p in self.P if p != 'LS']
        for i in self.I:
            for p in P_no_LS:
                for c in self.C:
                    self.prob += pulp.lpSum(self.PCF[i,p,c,v] for v in self.V) >= self.PX[i,p] + self.PY[i,c] - 1

        # (1.20) Transport Req
        for i in self.I:
            for p in P_no_LS:
                for c in self.C:
                    self.prob += pulp.lpSum(self.PLF[i,p,c,v] for v in self.V) >= self.PX[i,p] + self.PY[i,c] - 1

        # (1.21) Replenish Limit
        for i in self.I:
            for p in P_no_LS:
                for c in self.C:
                    self.prob += pulp.lpSum(self.PCF[i,p,c,v] for v in self.V) <= (self.PX[i,p] + self.PY[i,c]) * 0.5

        # (1.22) Transport Limit
        for i in self.I:
            for p in P_no_LS:
                for c in self.C:
                    self.prob += pulp.lpSum(self.PLF[i,p,c,v] for v in self.V) <= (self.PX[i,p] + self.PY[i,c]) * 0.5

        # (1.23) LS Transport
        if 'LS' in self.P:
            for i in self.I:
                self.prob += pulp.lpSum(self.PLF[i,'LS',c,v] for c in self.C for v in self.V) == self.PX[i,'LS']

        # (1.24) Fleet Capacity
        for v in self.V:
            lhs = 0
            # Replenishment
            for i in self.I:
                for p in self.P:
                    for c in self.C:
                        lhs += self.PCF[i,p,c,v] * self.params['t_ipcv_Re'].get((i,p,c,v), 0)
            # Transport
            for i in self.I:
                for p in ['BS', 'Seq']:
                    if p in self.P:
                        for c in self.C:
                            lhs += self.PLF[i,p,c,v] * self.params['t_ipcv_Tr'].get((i,p,c,v), 0)
            # SK
            if 'SK' in self.P:
                for w in self.W:
                    for c in self.C:
                        lhs += self.KLF[w,c,v] * self.params['t_wcv_SK'].get((w,c,v), 0)
            # TK
            if 'TK' in self.P:
                for c in self.C:
                    lhs += self.TLF[c,v] * self.params['t_1cv_TK'].get((c,v), 0)

            self.prob += lhs <= self.params['n_v'][v] * self.params['T']

        # (1.25) Seq Consistency
        if 'Seq' in self.P:
            for f in self.F:
                parts = self.I_f[f]
                for idx in range(len(parts)-1):
                    i, j = parts[idx], parts[idx+1]
                    for c in self.C:
                        for v in self.V:
                            self.prob += self.PLF[i,'Seq',c,v] == self.PLF[j,'Seq',c,v]

        # (1.26) SK Transport Rel
        if 'SK' in self.P:
            for w in self.W:
                for i in self.I_w.get(w, []):
                    for c in self.C:
                        for v in self.V:
                            self.prob += self.PLF[i,'SK',c,v] <= self.KLF[w,c,v]

        # (1.27) TK Transport Rel
        if 'TK' in self.P:
            for i in self.I:
                for c in self.C:
                    for v in self.V:
                        self.prob += self.PLF[i,'TK',c,v] <= self.TLF[c,v]

        # (1.28) Kit Usage Limit
        for w in self.W:
            self.prob += pulp.lpSum(self.KLF[w,c,v] for c in self.C for v in self.V) <= self.X_K[w]

        # (1.29) Max One TK
        if 'TK' in self.P:
            self.prob += pulp.lpSum(self.TLF[c,v] for c in self.C for v in self.V) <= 1

        # (1.30) TK Active Only If Parts
        if 'TK' in self.P:
            self.prob += pulp.lpSum(self.TLF[c,v] for c in self.C for v in self.V) <= pulp.lpSum(self.PX[i,'TK'] for i in self.I)

    def solve(self):
        status = self.prob.solve(pulp.PULP_CBC_CMD(msg=0))
        print(f"Status: {pulp.LpStatus[status]}")
        print(f"Objective Value: {pulp.value(self.prob.objective)}")
        return status

if __name__ == "__main__":
    print("Verifying TacticalAssemblyLineFeedingModel with Synthetic Data...")

    # Synthetic Data
    sets = {
        'V': ['V1'],
        'W': [1, 2],
        'I': ['P1', 'P2'],
        'F': ['F1'],
        'C': ['C1'],
        'P': ['LS', 'BS', 'Seq', 'SK', 'TK'],
        'I_f': {'F1': ['P1', 'P2']},
        'I_w': {1: ['P1'], 2: ['P2']},
        'F_w': {1: ['F1'], 2: ['F1']}
    }

    params = {
        'k_c_C': {'C1': 100},
        'k_w_W': {1: 50, 2: 50},
        'k_p_P': {'LS': 1, 'BS': 2, 'Seq': 1, 'SK': 3, 'TK': 3},
        'k_f_FV': {'F1': 5},
        'k_f_FW': {'F1': 10},
        'K_KV': 100,
        'K_KW': 200,
        'K_KP': 10,
        'n_v': {'V1': 2},
        'T': 100,
        'C_ipcv_Re': {('P1','LS','C1','V1'): 10},
        'C_ipc_P': {},
        'C_ipcv_T': {},
        'C_wcv_T': {},
        'C_cv_T': {},
        'C_ip_U': {('P1','LS'): 5},
        't_ipcv_Re': {},
        't_ipcv_Tr': {},
        't_wcv_SK': {},
        't_1cv_TK': {},
        'M': 1000
    }

    model = TacticalAssemblyLineFeedingModel(sets, params)
    model.build_model()
    model.solve()
