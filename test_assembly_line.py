
import unittest
from assembly_line_simulation import AssemblyLineSimulation, Task

class TestAssemblyLineSimulation(unittest.TestCase):

    def test_baseline_run(self):
        # Setup: 1 Worker, 1 Vehicle
        sim = AssemblyLineSimulation(num_workers_100_percent=1, num_vehicles_100_percent=1)

        # Add tasks: 2 tasks, duration 5 each
        task1 = Task(id=1, duration=5, workers_needed=1, vehicles_needed=1)
        task2 = Task(id=2, duration=5, workers_needed=1, vehicles_needed=1)

        sim.add_task(task1)
        sim.add_task(task2)

        # Run
        sim.run_simulation(duration=20)

        # Assertions
        # Task 1 should finish at T=6 (start 1, end 6)
        # Task 2 should finish at T=12 (start 7, end 12)

        self.assertTrue(task1.completed)
        self.assertTrue(task2.completed)
        self.assertEqual(len(sim.completed_tasks), 2)
        self.assertEqual(sim.time_step, 12)

        # Check utilization
        # Total time 12 steps.
        # Worker 1 worked 10 hours (5+5).
        # Paid 12 hours (12 steps).
        # Utilization = 10/12 ~ 0.833

        metrics = sim.calculate_metrics()
        self.assertAlmostEqual(metrics['worker_utilization'], 10/12, places=2)
        self.assertEqual(metrics['completed_tasks'], 2)

    def test_understaffing(self):
        # Setup: 2 Tasks needing 1 worker each.
        # With 2 workers, they run parallel. Time = 6.
        # With 1 worker (understaffing), they run sequential. Time = 12.

        # Baseline (2 workers)
        sim_base = AssemblyLineSimulation(num_workers_100_percent=2, num_vehicles_100_percent=2)
        sim_base.add_task(Task(1, 5, 1, 1))
        sim_base.add_task(Task(2, 5, 1, 1))
        sim_base.run_simulation(20)
        time_base = sim_base.time_step

        # Disruption (1 worker absent)
        sim_disrupt = AssemblyLineSimulation(num_workers_100_percent=2, num_vehicles_100_percent=2)
        sim_disrupt.apply_understaffing(1) # Remove 1 worker
        sim_disrupt.add_task(Task(1, 5, 1, 1))
        sim_disrupt.add_task(Task(2, 5, 1, 1))
        sim_disrupt.run_simulation(20)
        time_disrupt = sim_disrupt.time_step

        self.assertEqual(time_base, 6)
        self.assertEqual(time_disrupt, 12)

    def test_vehicle_breakdown(self):
        # Setup: 1 Task needing 1 vehicle.
        # Break all vehicles. Task should not start.

        sim = AssemblyLineSimulation(num_workers_100_percent=1, num_vehicles_100_percent=1)
        sim.apply_vehicle_breakdown(1)

        task1 = Task(1, 5, 1, 1)
        sim.add_task(task1)

        # Run for 10 steps
        sim.run_simulation(10)

        self.assertFalse(task1.completed)
        self.assertEqual(task1.progress, 0)

        # Repair and run
        sim.repair_vehicles()
        sim.run_simulation(10)
        self.assertTrue(task1.completed)

    def test_dependencies(self):
        # Setup: Task 2 depends on Task 1.
        # Resources: Infinite (enough for parallel).
        # Expected: Sequential execution.

        sim = AssemblyLineSimulation(num_workers_100_percent=10, num_vehicles_100_percent=10)
        task1 = Task(id=1, duration=5, workers_needed=1, vehicles_needed=1)
        task2 = Task(id=2, duration=5, workers_needed=1, vehicles_needed=1, dependencies=[1])

        sim.add_task(task1)
        sim.add_task(task2)

        sim.run_simulation(20)

        # Task 1 finishes at T=6.
        # Task 2 starts immediately in T=6 (immediate handoff). Ends T=11.
        self.assertEqual(sim.time_step, 11)

        # Check that Task 2 didn't start early
        # Can't check progress history here easily, but total time 12 confirms sequential.
        # If parallel, it would be 6.
        self.assertGreater(sim.time_step, 6)

if __name__ == '__main__':
    unittest.main()
