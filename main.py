
from assembly_line_simulation import AssemblyLineSimulation, Task
from data_parser import load_data_from_csv
from milp_model import TacticalAssemblyLineFeedingModel
import pulp

def main():
    print("=== Part 1: Solving Tactical Assembly Line Feeding MILP Model ===")
    sets, params = load_data_from_csv()

    if sets is None or params is None:
        print("Failed to load CSV data. Aborting.")
        return

    print(f"Data Loaded: {len(sets['I'])} Parts, {len(sets['W'])} Stations, {len(sets['V'])} Vehicles, {len(sets['C'])} Cells.")

    model = TacticalAssemblyLineFeedingModel(sets, params)
    model.build_model()
    print("Solving MILP model (this may take a moment)...")
    status = model.solve()

    if status == pulp.LpStatusOptimal:
        print("MILP Model Solved Optimally.")
    else:
        print(f"MILP Model Solution Status: {pulp.LpStatus[status]}")

    print("\n=== Part 2: Disruption Simulation ===")

    # Retrieve number of vehicles from the strategic data
    # We sum the baseline vehicles available
    total_vehicles_100_percent = sum(params['n_v'].values())
    # Assuming standard 100% service level for workers (user configurable)
    num_workers_100_percent = 40

    print(f"Baseline Service Level: {num_workers_100_percent} Workers, {total_vehicles_100_percent} Vehicles")

    sim_base = AssemblyLineSimulation(num_workers_100_percent=num_workers_100_percent, num_vehicles_100_percent=int(total_vehicles_100_percent))

    # Define placeholder Tasks for simulation to analyze efficiency based on the overall load
    # Here we create tasks that represent the operational assembly process
    # dependent on the strategic feeding solved above.

    # Task 1: Pre-assembly
    sim_base.add_task(Task(id=1, duration=10, workers_needed=2, vehicles_needed=0))
    # Task 2: Main Assembly (Needs vehicle for part transport)
    sim_base.add_task(Task(id=2, duration=20, workers_needed=4, vehicles_needed=1, dependencies=[1]))
    # Task 3: Quality Check
    sim_base.add_task(Task(id=3, duration=5, workers_needed=1, vehicles_needed=0, dependencies=[2]))

    print("\nRunning Baseline Simulation...")
    sim_base.run_simulation(duration=100)
    metrics_base = sim_base.calculate_metrics()
    print("Baseline Metrics:", metrics_base)

    print("\n--- Disruption Analysis ---")

    # Scenario A: Understaffing
    print("\nScenario: Understaffing (5 Workers Absent)")
    sim_understaffed = AssemblyLineSimulation(num_workers_100_percent, int(total_vehicles_100_percent))
    sim_understaffed.add_task(Task(1, 10, 2, 0))
    sim_understaffed.add_task(Task(2, 20, 4, 1, [1]))
    sim_understaffed.add_task(Task(3, 5, 1, 0, [2]))

    sim_understaffed.apply_understaffing(num_absent=5)
    sim_understaffed.run_simulation(duration=100)
    metrics_under = sim_understaffed.calculate_metrics()
    print("Understaffing Metrics:", metrics_under)

    # Scenario B: Vehicle Breakdown
    print("\nScenario: Vehicle Breakdown (1 Vehicle Broken)")
    sim_breakdown = AssemblyLineSimulation(num_workers_100_percent, int(total_vehicles_100_percent))
    sim_breakdown.add_task(Task(1, 10, 2, 0))
    sim_breakdown.add_task(Task(2, 20, 4, 1, [1]))
    sim_breakdown.add_task(Task(3, 5, 1, 0, [2]))

    sim_breakdown.apply_vehicle_breakdown(num_broken=1)
    sim_breakdown.run_simulation(duration=100)
    metrics_break = sim_breakdown.calculate_metrics()
    print("Breakdown Metrics:", metrics_break)

    print("\n--- Impact Analysis ---")
    print(f"Efficiency Loss (Understaffing): {metrics_base['throughput'] - metrics_under['throughput']:.4f} tasks/step")
    print(f"Efficiency Loss (Breakdown): {metrics_base['throughput'] - metrics_break['throughput']:.4f} tasks/step")

if __name__ == "__main__":
    main()
