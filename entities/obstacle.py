from utils.util_function import euclidean_distance_3d


class SphericalObstacle:
    """Initial implementation for the obstacle, stay tuned!"""

    def __init__(self, center, radius):
        self.center = center
        self.radius = radius

    def is_colliding(self, point):
        dist = euclidean_distance_3d(point, self.center)
        return dist <= self.radius

