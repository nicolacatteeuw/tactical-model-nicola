
import pandas as pd
import numpy as np
import os

def load_data_from_csv():
    # Load all csvs
    try:
        part_data = pd.read_csv('PartData.csv')
        vehicles_data = pd.read_csv('vehicles.csv')
        policies_data = pd.read_csv('policies.csv')
        layout_data = pd.read_csv('strategic_layout_output.csv')
        other_params = pd.read_csv('other_parameters.csv').set_index('variable name')

        # Determine presence of route data
        transport_route_exists = os.path.exists('TransportRoute.csv')
        if transport_route_exists:
            transport_route = pd.read_csv('TransportRoute.csv')

        replenishment_route_exists = os.path.exists('ReplenishmentRoute.csv')
        if replenishment_route_exists:
            replenishment_route = pd.read_csv('ReplenishmentRoute.csv')
    except FileNotFoundError as e:
        print(f"Error loading CSV files: {e}")
        return None, None

    # --- Build Sets ---
    V = vehicles_data['vehicle_id'].astype(str).tolist()

    # Workstations from parts data
    W = list(part_data['Station'].unique())
    # Ensure 1 is in W if needed (from constraints)
    if 1 not in W: W.append(1)

    I = part_data['Partnumber'].astype(str).tolist()
    F = part_data['Part_family'].astype(str).unique().tolist()
    C = layout_data['Cell'].astype(str).tolist()

    # Map policy names from CSV to internal abbreviations if needed, or use names directly.
    # The MILP code expects: ['LS', 'BS', 'Seq', 'SK', 'TK']
    policy_map = {
        'line stocking': 'LS',
        'boxed supply': 'BS',
        'sequencing': 'Seq',
        'stationary kit': 'SK',
        'travelling kit': 'TK'
    }

    # Create P list based on what's available
    # We add TK if not explicitly in policies but in layout (sometimes happens)
    P = ['LS', 'BS', 'Seq', 'SK', 'TK']

    # I_f: Dict mapping family f -> list of parts i
    I_f = {str(f): part_data[part_data['Part_family'].astype(str) == str(f)]['Partnumber'].astype(str).tolist() for f in F}

    # I_w: Dict mapping workstation w -> list of parts i
    I_w = {w: part_data[part_data['Station'].astype(str) == str(w)]['Partnumber'].astype(str).tolist() for w in W}

    # F_w: Dict mapping workstation w -> list of families f
    F_w = {w: part_data[part_data['Station'].astype(str) == str(w)]['Part_family'].astype(str).unique().tolist() for w in W}

    sets = {
        'V': V,
        'W': W,
        'I': I,
        'F': F,
        'C': C,
        'P': P,
        'I_f': I_f,
        'I_w': I_w,
        'F_w': F_w
    }

    # --- Build Params ---
    params = {}

    # k_c_C: Capacity of cell c
    # The 'Size' column in layout_data represents capacity?
    params['k_c_C'] = {str(row['Cell']): row['Size'] for _, row in layout_data.iterrows()}

    # k_w_W: Capacity of workstation w. Assumed infinite or some large number if not specified.
    # We don't have this in CSV directly, setting to a large number to prevent infeasibility.
    params['k_w_W'] = {w: 1000 for w in W}

    # k_p_P: Space required for policy p
    # Map from policies_data
    params['k_p_P'] = {}
    for p_id in P:
        params['k_p_P'][p_id] = 1 # default

    for _, row in policies_data.iterrows():
        mapped_pol = policy_map.get(row['policy_name'].lower().strip(), None)
        if mapped_pol:
            params['k_p_P'][mapped_pol] = row['policy_capacity_volume']

    # TK might not be in policies.csv, set a default if missing
    if 'TK' not in params['k_p_P']: params['k_p_P']['TK'] = 1

    # k_f_FV: Volume of part family f
    # Calculate average volume of parts in family
    k_f_FV = {}
    for f in F:
        k_f_FV[f] = part_data[part_data['Part_family'] == int(f)]['Part_volume'].mean()
    params['k_f_FV'] = k_f_FV

    # k_f_FW: Weight of part family f
    k_f_FW = {}
    for f in F:
        k_f_FW[f] = part_data[part_data['Part_family'] == int(f)]['Part_weight'].mean()
    params['k_f_FW'] = k_f_FW

    # K_KV, K_KW: Kit capacities (assuming 100 for volume, 200 for weight, or derive from vehicles?)
    params['K_KV'] = 100 # Default if not specified
    params['K_KW'] = 500 # Default if not specified

    # K_KP: Space for Kit
    params['K_KP'] = 10

    # n_v: Number of vehicles
    params['n_v'] = {str(row['vehicle_id']): row['number_of_vehicles'] for _, row in vehicles_data.iterrows()}

    # T: Takt time (derive from demand?)
    total_demand = 175
    try:
        total_demand = float(other_params.loc['total_demand', 'value'])
    except:
        pass
    # Assume some operational time, e.g., 8 hours = 28800 seconds
    params['T'] = 28800 / total_demand if total_demand > 0 else 100

    # Costs
    # C_ipcv_Re, C_ipc_P, C_ipcv_T, C_wcv_T, C_cv_T, C_ip_U
    # We will initialize them to 0 or derive simple estimates
    params['C_ipcv_Re'] = {}
    params['C_ipc_P'] = {}
    params['C_ipcv_T'] = {}
    params['C_wcv_T'] = {}
    params['C_cv_T'] = {}
    params['C_ip_U'] = {}

    # t_ipcv_Re, t_ipcv_Tr, t_wcv_SK, t_1cv_TK
    params['t_ipcv_Re'] = {}
    params['t_ipcv_Tr'] = {}
    params['t_wcv_SK'] = {}
    params['t_1cv_TK'] = {}

    params['M'] = 10000

    # Basic Population of Cost based on distance / speed / wage
    try:
        wage_log = float(other_params.loc['wage_logistic', 'value'])
    except:
        wage_log = 25

    # Iterate to fill costs and times (simplified placeholder logic)
    # Real data would need explicit distance matrices. We will use a baseline value.
    for v in V:
        v_data = vehicles_data[vehicles_data['vehicle_id'] == int(v)].iloc[0]
        speed = v_data['vehicle_speed'] # m/h
        cost_ph = v_data['usage cost per hour'] + wage_log

        # Assign basic values
        for i in I:
            for p in P:
                for c in C:
                    time_val = 0.1 # Example 0.1 hour
                    params['t_ipcv_Re'][(i,p,c,v)] = time_val
                    params['C_ipcv_Re'][(i,p,c,v)] = time_val * cost_ph

                    params['t_ipcv_Tr'][(i,p,c,v)] = time_val
                    params['C_ipcv_T'][(i,p,c,v)] = time_val * cost_ph

        for w in W:
            for c in C:
                time_val = 0.15
                params['t_wcv_SK'][(w,c,v)] = time_val
                params['C_wcv_T'][(w,c,v)] = time_val * cost_ph

        for c in C:
             time_val = 0.2
             params['t_1cv_TK'][(c,v)] = time_val
             params['C_cv_T'][(c,v)] = time_val * cost_ph

    # Fill Preparation and Usage Costs (independent of vehicle)
    # Using 'search time Preparation' and 'search time Usage' from policies
    for i in I:
        for p in P:
             p_row = policies_data[policies_data['policy_name'].str.lower() == {v: k for k, v in policy_map.items()}.get(p, '')]
             prep_time = p_row['search time Preparation (h)'].values[0] if len(p_row) > 0 else 0
             use_time = p_row['search time Usage (h)'].values[0] if len(p_row) > 0 else 0

             for c in C:
                 params['C_ipc_P'][(i,p,c)] = prep_time * wage_log

             try:
                 wage_ass = float(other_params.loc['wage_assembly', 'value'])
             except:
                 wage_ass = 40
             params['C_ip_U'][(i,p)] = use_time * wage_ass

    return sets, params

if __name__ == '__main__':
    s, p = load_data_from_csv()
    if s and p:
        print(f"Loaded {len(s['I'])} parts, {len(s['V'])} vehicles, {len(s['W'])} workstations, {len(s['C'])} cells.")
