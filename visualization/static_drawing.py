import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from utils import config
from utils.util_function import euclidean_distance_3d
from phy.large_scale_fading import maximum_communication_range


def scatter_plot(simulator):
    """Draw a static scatter plot, includes communication edges (without obstacles)"""

    fig = plt.figure()
    ax = fig.add_axes(Axes3D(fig))

    for drone1 in simulator.drones:
        for drone2 in simulator.drones:
            if drone1.identifier != drone2.identifier:
                ax.scatter(drone1.coords[0], drone1.coords[1], drone1.coords[2], c='red', s=30)
                distance = euclidean_distance_3d(drone1.coords, drone2.coords)
                if distance <= maximum_communication_range():
                    x = [drone1.coords[0], drone2.coords[0]]
                    y = [drone1.coords[1], drone2.coords[1]]
                    z = [drone1.coords[2], drone2.coords[2]]
                    ax.plot(x, y, z, color='black', linestyle='dashed', linewidth=1)

    ax.set_xlim(0, config.MAP_LENGTH)
    ax.set_ylim(0, config.MAP_WIDTH)
    ax.set_zlim(0, config.MAP_HEIGHT)

    # maintain the proportion of the x, y and z axes
    ax.set_box_aspect([config.MAP_LENGTH, config.MAP_WIDTH, config.MAP_HEIGHT])

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')

    plt.show()

def draw_sphere(ax, center, radius, color='skyblue', alpha=0.6):
    u = np.linspace(0, 2 * np.pi, 50)
    v = np.linspace(0, np.pi, 50)
    x = center[0] + radius * np.outer(np.cos(u), np.sin(v))
    y = center[1] + radius * np.outer(np.sin(u), np.sin(v))
    z = center[2] + radius * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(x, y, z, color=color, alpha=alpha, edgecolor='k')

def scatter_plot_with_spherical_obstacles(simulator):
    # TODO: handle the case when the obstacle has a part that extends beyond the map

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for so in simulator.obstacles:
        draw_sphere(ax, so.center, so.radius)

    ax.set_xlim(0, config.MAP_LENGTH)
    ax.set_ylim(0, config.MAP_WIDTH)
    ax.set_zlim(0, config.MAP_HEIGHT)

    # maintain the proportion of the x, y and z axes
    ax.set_box_aspect([config.MAP_LENGTH, config.MAP_WIDTH, config.MAP_HEIGHT])

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')

    plt.show()
