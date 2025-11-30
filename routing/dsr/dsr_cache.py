class DSRCache:
    """Minimal per-node cache for DSR path storage."""
    def __init__(self):
        self.routes = {}  # dest_id -> [path list]

    def learn(self, dest, path):
        """Add or replace a route if it's shorter than existing."""
        if not path:
            return
        if dest not in self.routes or len(path) < len(self.routes[dest]):
            self.routes[dest] = list(path)

    def lookup(self, dest):
        """Return a known route, or None if not found."""
        return self.routes.get(dest)

    def forget(self, dest):
        """Remove route associated with a broken link or destination."""
        if dest in self.routes:
            del self.routes[dest]
