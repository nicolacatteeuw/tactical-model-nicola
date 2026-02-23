
class Worker:
    def __init__(self, id, skill_level=1.0, wage_rate=20.0):
        self.id = id
        self.skill_level = skill_level
        self.wage_rate = wage_rate
        self.is_busy = False
        self.is_absent = False
        self.current_task = None
        self.hours_worked = 0.0 # Actual busy time
        self.hours_paid = 0.0   # Time on the clock

class Vehicle:
    def __init__(self, id, capacity=1, cost_per_hour=10.0):
        self.id = id
        self.capacity = capacity
        self.cost_per_hour = cost_per_hour
        self.is_broken_down = False
        self.is_busy = False
        self.current_task = None
        self.hours_used = 0.0

class Task:
    def __init__(self, id, duration, workers_needed=1, vehicles_needed=0, dependencies=None):
        self.id = id
        self.duration = duration
        self.workers_needed = workers_needed
        self.vehicles_needed = vehicles_needed
        self.dependencies = dependencies if dependencies else [] # List of Task IDs
        self.completed = False
        self.progress = 0
        self.assigned_workers = []
        self.assigned_vehicles = []

class AssemblyLineSimulation:
    def __init__(self, num_workers_100_percent, num_vehicles_100_percent):
        self.num_workers_100_percent = num_workers_100_percent
        self.num_vehicles_100_percent = num_vehicles_100_percent

        self.workers = [Worker(i) for i in range(num_workers_100_percent)]
        self.vehicles = [Vehicle(i) for i in range(num_vehicles_100_percent)]
        self.tasks = []
        self.task_map = {} # ID -> Task object
        self.time_step = 0
        self.completed_tasks = []

    def add_task(self, task):
        self.tasks.append(task)
        self.task_map[task.id] = task

    def apply_understaffing(self, num_absent):
        """Mark a number of workers as absent."""
        count = 0
        for worker in self.workers:
            if not worker.is_absent and not worker.is_busy:
                worker.is_absent = True
                count += 1
                if count >= num_absent:
                    break
        print(f"Understaffing applied: {count} workers absent.")

    def restore_staffing(self):
        """Restore all absent workers."""
        for worker in self.workers:
            worker.is_absent = False
        print("Staffing restored.")

    def apply_vehicle_breakdown(self, num_broken):
        """Mark a number of vehicles as broken down."""
        count = 0
        for vehicle in self.vehicles:
            if not vehicle.is_broken_down and not vehicle.is_busy:
                vehicle.is_broken_down = True
                count += 1
                if count >= num_broken:
                    break
        print(f"Vehicle breakdown applied: {count} vehicles broken.")

    def repair_vehicles(self):
        """Repair all broken vehicles."""
        for vehicle in self.vehicles:
            vehicle.is_broken_down = False
        print("Vehicles repaired.")

    def run_step(self):
        """Simulate one time step of the assembly line."""
        self.time_step += 1

        # Track active resources for metrics
        step_duration = 1.0

        # Identify available resources (excluding busy, absent, or broken)
        available_workers = [w for w in self.workers if not w.is_busy and not w.is_absent]
        available_vehicles = [v for v in self.vehicles if not v.is_busy and not v.is_broken_down]

        # Process tasks
        for task in self.tasks:
            if task.completed:
                continue

            # Check dependencies
            dependencies_met = True
            for dep_id in task.dependencies:
                if dep_id in self.task_map:
                    if not self.task_map[dep_id].completed:
                        dependencies_met = False
                        break
                else:
                    # Dependency not found, assume met? Or raise error?
                    # For robustness, assume not met if missing implies complex setup.
                    # Or assume met if user made typo?
                    # Let's assume NOT met to prevent out-of-order execution.
                    dependencies_met = False
                    break

            if not dependencies_met:
                continue

            if task.progress == 0:
                # Try to start task
                if len(available_workers) >= task.workers_needed and len(available_vehicles) >= task.vehicles_needed:
                    # Allocate resources
                    for _ in range(task.workers_needed):
                        worker = available_workers.pop(0)
                        worker.is_busy = True
                        worker.current_task = task
                        task.assigned_workers.append(worker)

                    for _ in range(task.vehicles_needed):
                        vehicle = available_vehicles.pop(0)
                        vehicle.is_busy = True
                        vehicle.current_task = task
                        task.assigned_vehicles.append(vehicle)

                    task.progress = 1 # Start task
                else:
                    # Task waits
                    pass

            elif task.progress > 0:
                # Task is running
                task.progress += 1

                # Check for completion
                if task.progress > task.duration:
                    task.completed = True
                    self.completed_tasks.append(task)

                    # Release resources
                    for worker in task.assigned_workers:
                        worker.is_busy = False
                        worker.current_task = None
                    task.assigned_workers = []

                    for vehicle in task.assigned_vehicles:
                        vehicle.is_busy = False
                        vehicle.current_task = None
                    task.assigned_vehicles = []

        # Update metrics
        for worker in self.workers:
            if not worker.is_absent:
                worker.hours_paid += step_duration
            if worker.is_busy:
                worker.hours_worked += step_duration

        for vehicle in self.vehicles:
            if vehicle.is_busy:
                vehicle.hours_used += step_duration

    def run_simulation(self, duration):
        """Run the simulation for a specific duration."""
        for _ in range(duration):
            self.run_step()
            if len(self.completed_tasks) == len(self.tasks):
                break

    def calculate_metrics(self):
        """Calculate efficiency, wages, and other costs."""
        total_wages = sum(w.hours_paid * w.wage_rate for w in self.workers)
        total_vehicle_cost = sum(v.hours_used * v.cost_per_hour for v in self.vehicles)

        # Utilization: Total Worked Hours / Total Paid Hours
        total_paid_hours = sum(w.hours_paid for w in self.workers)
        utilization = sum(w.hours_worked for w in self.workers) / total_paid_hours if total_paid_hours > 0 else 0

        # Throughput: Tasks per hour
        throughput = len(self.completed_tasks) / self.time_step if self.time_step > 0 else 0

        return {
            "total_wages": total_wages,
            "total_vehicle_cost": total_vehicle_cost,
            "total_cost": total_wages + total_vehicle_cost,
            "worker_utilization": utilization,
            "throughput": throughput,
            "simulation_time": self.time_step,
            "completed_tasks": len(self.completed_tasks)
        }
