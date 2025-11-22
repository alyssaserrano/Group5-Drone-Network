import random
from phy.channel import Channel
from simulator.log import logger


class ProbChannel(Channel):
    """
    Simple channel model that simply simulates
    data loss with a preset probability.
       
    """
    def __init__(self, env, loss_prob=0.15): # 15% loss by default
        super().__init__(env) # calls original channel setup
        self.loss_prob = loss_prob # store loss probability
        
    def drop_packet(self):
        """
        decide whether packet is dropped
        returns True if random produces a number less than 0.15, False otherwise
        """
        result = random.random() < self.loss_prob
        return result
    
    #Override unicast to add preset packet loss feature
    def unicast_put(self, value, dst_id):
        """
        one-to-one communcation 
        calls our drop_packet method to decide if packet is lost
        if lost, print it the log
        else call the original unicast_put method
        """
        #print(f"[DEBUG] ProbChannel.unicast_put called for dst_id={dst_id}")
        if self.drop_packet():
            #logger.info(f"[CHANNEL] Unicast packet to drone {dst_id} LOST (p={self.loss_prob})")
            return
        super().unicast_put(value, dst_id)
        
    def broadcast_put(self, value):
        """
        same here just loops through all drones (broadcast)
        
        """
        #print(f"[DEBUG] ProbChannel.broadcast_put called")
        #print(f"[DEBUG] pipes keys: {list(self.pipes.keys())}")
        for key in self.pipes.keys():
            if self.drop_packet():
                #logger.info(f"[CHANNEL] Broadcast packet to drone {key} LOST (p={self.loss_prob})")
                continue
            super().unicast_put(value, key)
            
    def multicast_put(self, value, dst_id_list):
        """
        same here just loops through specific group of drones (multicast)
        """
        #print(f"[DEBUG] ProbChannel.multicast_put called")
        for dst_id in dst_id_list:
            if self.drop_packet():
                #print(f"[CHANNEL] Multicast packet to drone {dst_id} LOST (p={self.loss_prob})")
                continue
            super().unicast_put(value, dst_id)
            
# testing if code above works standalone before connecting to rest of simulator    

if __name__ == "__main__":
    print("[TEST] Running ProbChannel standalone test for unicast...")

    from types import SimpleNamespace
    dummy_env = SimpleNamespace()
    channel = ProbChannel(dummy_env)
    channel.pipes = {0: [],
                     1: [],
                     2: [],
                     3: [],
                     4: []}  # two fake drones

    print("[TEST] Sending packet...")
    channel.unicast_put(["test_packet", 0, "drone0"], 1)
    print("[TEST] Channel state:")
    print("Drone 1 inbox:", channel.pipes[1])
    print("\n")
    
    print("[TEST] Running ProbChannel standalone test for broadcast...")
    print("[TEST] Sending packet...")
    channel.broadcast_put(["test_packet", 0, "drone0"])
    print("[TEST] Channel state:")
    for i in range(5):
        print(f"Drone {i} inbox:", channel.pipes[i])
    print("\n")
    
    print("[TEST] Running ProbChannel standalone test for multicast...")
    print("[TEST] Sending packet...")
    channel.multicast_put(["test_packet", 0, "drone0"], [1,3,4])
    print("[TEST] Channel state:")
    for i in [1, 3, 4]:
        print(f"Drone {i} inbox:", channel.pipes[i])
    print("\n")
    
    
    



