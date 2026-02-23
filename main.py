
from assembly_line_simulation import AssemblyLineSimulation, Task

def main():
    print("Initializing Tactical Assembly Line Model...")

    # 1. Define Service Level Inputs (Baseline)
    # The user should enter the 100% service level requirements here.
    # Example: 40 workers and 20 vehicles.
    num_workers = 40
    num_vehicles = 20

    print(f"Service Level: {num_workers} Workers, {num_vehicles} Vehicles")

    sim = AssemblyLineSimulation(num_workers_100_percent=num_workers, num_vehicles_100_percent=num_vehicles)

    # 2. Define Tasks based on the Tactical Model (12 Images)
    # TODO: Replace the example tasks below with the specific tasks from the provided images.
    # Each Task should define:
    # - id: Unique identifier
    # - duration: Time steps to complete
    # - workers_needed: Number of workers required
    # - vehicles_needed: Number of vehicles required
    # - dependencies: List of task IDs that must complete before this task starts

    # Example Placeholder Tasks:
    # Task 1: Pre-assembly (Duration 10, Needs 2 Workers)
    sim.add_task(Task(id=1, duration=10, workers_needed=2, vehicles_needed=0))

    # Task 2: Main Assembly (Duration 20, Needs 4 Workers, 1 Vehicle, Depends on Task 1)
    sim.add_task(Task(id=2, duration=20, workers_needed=4, vehicles_needed=1, dependencies=[1]))

    # Task 3: Quality Check (Duration 5, Needs 1 Worker, Depends on Task 2)
    sim.add_task(Task(id=3, duration=5, workers_needed=1, vehicles_needed=0, dependencies=[2]))

    # ... Add remaining tasks from the model ...

    print(f"Added {len(sim.tasks)} tasks to the simulation.")

    # 3. Run Baseline Simulation
    print("\nRunning Baseline Simulation...")
    sim.run_simulation(duration=100)
    metrics_base = sim.calculate_metrics()
    print("Baseline Metrics:", metrics_base)

    # 4. Analyze Disruptions
    print("\n--- Disruption Analysis ---")

    # Scenario A: Understaffing (Short term)
    print("\nScenario: Understaffing (5 Workers Absent)")
    sim_understaffed = AssemblyLineSimulation(num_workers, num_vehicles)
    # Re-add tasks (need to recreate objects or deep copy)
    sim_understaffed.add_task(Task(1, 10, 2, 0))
    sim_understaffed.add_task(Task(2, 20, 4, 1, [1]))
    sim_understaffed.add_task(Task(3, 5, 1, 0, [2]))

    sim_understaffed.apply_understaffing(num_absent=5)
    sim_understaffed.run_simulation(duration=100)
    metrics_under = sim_understaffed.calculate_metrics()
    print("Understaffing Metrics:", metrics_under)

    # Scenario B: Vehicle Breakdown
    print("\nScenario: Vehicle Breakdown (2 Vehicles Broken)")
    sim_breakdown = AssemblyLineSimulation(num_workers, num_vehicles)
    sim_breakdown.add_task(Task(1, 10, 2, 0))
    sim_breakdown.add_task(Task(2, 20, 4, 1, [1]))
    sim_breakdown.add_task(Task(3, 5, 1, 0, [2]))

    sim_breakdown.apply_vehicle_breakdown(num_broken=2)
    sim_breakdown.run_simulation(duration=100)
    metrics_break = sim_breakdown.calculate_metrics()
    print("Breakdown Metrics:", metrics_break)

    # Comparison
    print("\n--- Impact Analysis ---")
    print(f"Efficiency Loss (Understaffing): {metrics_base['throughput'] - metrics_under['throughput']:.4f} tasks/step")
    print(f"Efficiency Loss (Breakdown): {metrics_base['throughput'] - metrics_break['throughput']:.4f} tasks/step")

if __name__ == "__main__":
    main()
