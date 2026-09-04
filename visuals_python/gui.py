import tkinter as tk
from tkinter import ttk
import threading


class Gui:
    def __init__(self, variables):
        self.variables = variables
        self.window = tk.Tk()
        self.window.title("Simulation Controls")

        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_spawn = tk.Frame(self.notebook)
        self.tab_physics = tk.Frame(self.notebook)
        self.tab_visuals = tk.Frame(self.notebook)
        self.tab_walls = tk.Frame(self.notebook)

        self.notebook.add(self.tab_spawn, text="Spawning")
        self.notebook.add(self.tab_physics, text="Physics")
        self.notebook.add(self.tab_visuals, text="Visuals")
        self.notebook.add(self.tab_walls, text="Walls")

        self.create_trigger_button(self.tab_spawn, "Restart Simulation", self.variables, "RESTART_CLICKED")
        self.create_slider_vector(self.tab_spawn, "Starting position X range", 0.0, 2000.0,
                                  self.variables["STARTING_POSITION_X"], is_int=True)
        self.create_slider_vector(self.tab_spawn, "Starting position Y range", 0.0, 1100.0,
                                  self.variables["STARTING_POSITION_Y"], is_int=True)
        self.create_slider_vector(self.tab_spawn, "Starting speed X range", -5000.0, 5000.0,
                                  self.variables["STARTING_SPEED_X"], is_int=True)
        self.create_slider_vector(self.tab_spawn, "Starting speed Y range", -5000.0, 5000.0,
                                  self.variables["STARTING_SPEED_Y"], is_int=True)
        self.create_slider_single(self.tab_spawn, "Spawned particle count", 1, self.variables["MAX_PARTICLES"], self.variables,
                                  "STARTING_PARTICLE_COUNT" , is_int=True)
        self.create_slider_single(self.tab_spawn, "Random wall count", 0.0, 50.0,
                                  self.variables , "RANDOM_WALL_COUNT", is_int=True)
        self.create_slider_single(self.tab_spawn, "Random wall max len", 0.0, 2000.0,
                                  self.variables , "RANDOM_WALL_MAX_LEN", is_int=True)
        self.create_slider_vector(self.tab_spawn, "Window size", 0.0, 3000.0, self.variables["NEW_MAP_SIZE"])


        self.create_slider_vector(self.tab_physics, "Gravity", -1000.0, 1000.0, self.variables["GRAVITY"])
        self.create_slider_single(self.tab_physics, "Max Influence Dist", 1, 100, self.variables,
                                  "MAX_INFLUENCE_DISTANCE")
        self.create_slider_single(self.tab_physics, "Target Density", 1000, 500000, self.variables, "TARGET_DENSITY")
        self.create_slider_single(self.tab_physics, "Pressure Multiplier", 0.00001, 0.001, self.variables,
                                  "PRESSURE_MULTIPLIER", resolution=0.00001)
        self.create_slider_single(self.tab_physics, "Collision Dampening", 0.0, 1.0, self.variables,
                                  "COLLISION_DAMPENING")
        self.create_slider_single(self.tab_physics, "Viscosity", 0.0, 10.0, self.variables, "VISCOSITY")
        self.create_slider_single(self.tab_physics, "Friction Multiplier", 0.0, 1.0, self.variables,
                                  "FRICTION_MULTIPLIER" , resolution=0.001)
        self.create_slider_single(self.tab_physics, "Wall Default Push", 0.0, 10.0, self.variables, "WALL_DEFAULT_PUSH")


        self.create_slider_single(self.tab_visuals, "Visual Radius", 1, 20, self.variables, "VISUAL_RADIUS",
                                  is_int=True)
        self.create_slider_single(self.tab_visuals, "Visual Color Mult", 10000, 500000, self.variables,
                                  "VISUAL_COLOUR_PRESSURE_MULTIPLIER", is_int=True)

        self.create_trigger_button(self.tab_walls, "Add Wall", self.variables, "ADD_WALL_CLICKED")
        self.create_trigger_button(self.tab_walls, "Remove Wall", self.variables, "REMOVE_WALL_CLICKED")
        self.create_slider_vector(self.tab_walls, "Wall point 1", -100.0, 3000,
                                  self.variables["WALL_POINT_1"], is_int=True)
        self.create_slider_vector(self.tab_walls, "Wall point 2", -100.0, 3000,
                                  self.variables["WALL_POINT_2"], is_int=True)




    def run(self):
        self.window.mainloop()

    def create_slider_vector(self, parent, label, min_val, max_val, target_obj, is_int=False, resolution=None,
                             padding_y=2, padding_x=20):
        if resolution is None:
            resolution = 1 if is_int else 0.01

        def build_component(axis):
            frame = tk.Frame(parent)
            frame.pack(padx=padding_x, pady=padding_y, fill=tk.X)
            initial_val = getattr(target_obj, axis)
            if is_int:
                initial_val = int(initial_val)
            entry_var = tk.StringVar(value=str(initial_val))

            def on_slider_move(val):
                v = float(val)
                if is_int:
                    v = int(v)
                setattr(target_obj, axis, v)
                entry_var.set(str(v))

            def on_entry_type(event):
                try:
                    v = float(entry_var.get())
                    slider.set(v)
                except ValueError:
                    pass

            slider = tk.Scale(
                frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL,
                label=f"{label} {axis.upper()}", resolution=resolution, command=on_slider_move
            )
            slider.set(getattr(target_obj, axis))
            slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

            entry = tk.Entry(frame, textvariable=entry_var, width=8)
            entry.pack(side=tk.RIGHT, padx=(10, 0), pady=(15, 0))
            entry.bind("<Return>", on_entry_type)
            entry.bind("<FocusOut>", on_entry_type)

        build_component('x')
        build_component('y')

    def create_slider_single(self, parent, label, min_val, max_val, target_dict, key, is_int=False, resolution=None):
        if resolution is None:
            resolution = 1 if is_int else 0.01

        frame = tk.Frame(parent)
        frame.pack(padx=20, pady=2, fill=tk.X)
        entry_var = tk.StringVar(value=str(target_dict[key]))

        def on_slider_move(val):
            v = float(val)
            if is_int:
                v = int(v)
            target_dict[key] = v
            entry_var.set(str(v))

        def on_entry_type(event):
            try:
                v = float(entry_var.get())
                slider.set(v)
            except ValueError:
                pass

        slider = tk.Scale(
            frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL, label=label,
            resolution=resolution, command=on_slider_move
        )
        slider.set(target_dict[key])
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        entry = tk.Entry(frame, textvariable=entry_var, width=8)
        entry.pack(side=tk.RIGHT, padx=(10, 0), pady=(15, 0))
        entry.bind("<Return>", on_entry_type)
        entry.bind("<FocusOut>", on_entry_type)

    def create_trigger_button(self, parent, label, target_dict, key):
        button = tk.Button(
            parent, text=label,
            command=lambda: target_dict.update({key: True}),
            bg="#d9534f", fg="white", font=("Arial", 10, "bold")
        )
        button.pack(padx=20, pady=10, fill=tk.X)
        return button


def start_gui_thread(variables):
    def thread_target():
        gui = Gui(variables)
        gui.run()

    threading.Thread(target=thread_target, daemon=True).start()