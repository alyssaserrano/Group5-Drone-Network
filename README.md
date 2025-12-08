# User Manual

Group 5: Alyssa Serrano, Afnan Algharbi, Halie Do, Reiner Bondoc,

Cristian Carino, Evan Tardiff, Andrew-Jacob Santons, Sergio Fernandez

Donneys, Jahnavi Panchal

CS 576 - Computer Networks and Distributed Systems

Professor Umut Can Cabuk

## Fall 2025


## Table of Contents

- 1. Introduction...................................................................................................
   - 1.2 Features Implemented...........................................................................
   - 1.3 How the Simulation Runs.........................................................................................
- 2. System Requirements and Installations...........................................................................
   - 2.1 Software Requirements............................................................................................
   - 2.2 Hardware Requirements...........................................................................................
- 3. Code structure and Files Overview..................................................................................
   - 3.1 Codebase..................................................................................................................
- 4. Testing and Evaluation.....................................................................................................
   - 4.1 Testing Methodology................................................................................................
   - 4.2 Testing Mobility vs Latency.....................................................................................
      - 4.2.1 Scenario 1: Leader-Follower with AODV.......................................................
      - 4.2.2 Testing Scenario 2: Leader-Follower with OLSR............................................
      - 4.2.3 Scenario 3: Random Waypoint with AODV....................................................
   - 4.3 Energy.....................................................................................................................
      - 4.3.1 Throughput tradeoff: TX power levels vs lifetime/PDR...............................
      - Tested with four drones:..........................................................................................
      - 4.3.2 : AODV vs. OLSR.........................................................................................
   - 4.4 Formation Transition..............................................................................................
- 5. Statement of Work........................................................................................................
- 6. Conclusion References...................................................................................................


## 1. Introduction...................................................................................................

1.1 purpose of the Simulator
Our project is a drone network simulation that communicates between four drones and forms a V
or line alignment. Our work extends from that from a python-based drone simulator. With the
accessible simulator we were able to implement all custom requirements of the Physical, MAC,
Networks, mobility, and GUI expectations. This project aims to address the challenges in drone
communication and focuses on the challenges of topology and formation of multiple drones in
network communication. Users can configure:

- which routing protocol to execute (AODV vs OLSR)
- which mobility model to employ (e.g., Random Walk, Gaussian Markov, etc.)
- what channel model to implement (Default Channel vs ProbChannel)
- path planning and visualisation settings.
The simulator is designed for students, educators, and researchers to evaluate, learn, and
experiment with the effects of mobility, interference, and dynamics of wireless channel
interactions (i.e., packet deliveries, collisions, and routing behaviors).

### 1.2 Features Implemented...........................................................................

1. Physical: The physical layer consists of both a WiFi-802.11n/ac and Wi-Fi Direct
    connection. There is simulated probability loss and the power levels are defined for
    TX/RX/idle/sleep/energy.
2. MAC: The MAC layer manages reliable unicast communication using CSMA/CA with
    p-persistent backoff for collision avoidance and an ACK/Retry mechanism with
    exponential backoff for transmission reliability.
3. Routing/Network: The network layer consists of the implementation of two protocols: a
    reactive protocol, AODV (Ad hoc On-Demand Distance Vector) and a proactive protocol,
    OLSR (Optimized Link State Routing Protocol). AODV is designed for on demand route
    discovery while on the other hand, OLSR is designed for periodic HELLO/TC messaging
    and proactively updated in the network.
4. Mobility: The mobility layer defines how the drones move through the 3D simulation
    space and directly shapes network connectivity over time. There are different mobility
    models, including Gauss Markov 3D which it generates smooth, memory-based random
    motion. There is a Random Walk 3D, where it changes directions at fixed intervals, and a
    Random Waypoint 3D, where drones travel between randomly generated waypoints. Last,
    the Leader follower/Formation mobility, where the leader navigates the map and
    followers maintain structured offsets that can switch mid-sun. Each model updates drone


```
positions at fixed time steps, influencing path loss link availability, and routing churn
while the system logs mobility topology changes to support experiments on formation
transitions, stability, and overall network performance.
```
5. GUI & Visualization: This layer consists of an interactive 3d visualization of the
    simulation area that displays all drones, their current positions, and the link relationships
    in real time. The interface provides play/pause and reset controls, as well as a time slider
    to go through the simulation timeline. Each drone is annotated with its ID, a battery bar,
    and a queue-size indicator to show how busy it is. The side panels display live metrics
    such as PDR, latency, jitter, routing overhead, and per-drone statistics, with options to
    export plots and raw data to PNG/CSV for later analysis.
6. Experiments: We conducted experiments using different mobilities and routing protocols
    and collected the appropriate metrics. A section in this manual is dedicated to discuss
    them.

### 1.3 How the Simulation Runs.........................................................................................

Step 1 - Running main.py:
main.py is responsible for activating the whole simulation. Through running it, the SimPy
environment is created, the simulator is initialized and so are the drones. Then the mobility
model gets assigned, alongside the routing protocol and channel type.

Step 2 - Running of the simulation:
In the background, Simpy executes the drone mobility updates, routing processes, CSMA/CA
backoff and channel sensing, any PHY transmissions, and packet delivery transmissions
including retransmissions after ACK timeout and any metrics updates.

Step 3 - Visualization:
At the end of the run, the user will be able to view the compiled positions and communication
logs generated, a GIF animation of the scene and an interactive UI as shown below.


## 2. System Requirements and Installations...........................................................................

This section specifies software requirements necessary to install and execute simulator
applications. The simulator utilizes Python, which allows it to be fast and able to run on any
operating system (OS) with no hardware constraints because of its use of SimPy and scientific
computing tools.

### 2.1 Software Requirements............................................................................................

- Python 3.10 or 3.
- Required Python Packages:
    - Simpy
    - Numpy
    - Matplotlib
    - Pillow
    - mpl_toolkits.plot3d
- Recommended platform:
    - Linux (Ubuntu 20.04 / 22.04)
    - macOS also works
    - Windows + WSL supported


### 2.2 Hardware Requirements

This simulator is not heavy computationally, however the visualizations and long duration
simulations will produce hundreds of frames requiring the minimum dual-core CPu and 4 GB
RAM.

## 3. Code structure and Files Overview..................................................................................

This section describes how the simulator project is structured and what the main files do. The
organization of the folders makes it easy for new users to find the routing logic, mobility models,
visualization modules, channel behavior, and simulator configuration for the simulation project.

### 3.1 Codebase..................................................................................................................

```
1) Download or clone the repository: Group5-Drone-Network.git
2) Ensure the folders contain the files mentioned below
3) To ensure the correct version of python packages are being using, create a virtual
environment
4) Install the dependencies in requirements.txt
5) Once the installation is complete, you may run main.py and do the following:
a) alter the number of drones, mobility model, and channel selection.
b) Enable visualization
c) Alter the simulation time
6) You can manipulate drone.py to run the simulation with different protocols
```


## 4. Testing and Evaluation.....................................................................................................

This section will present results from research which has been conducted using the Network
Simulator as part of several different scenarios using various routing protocols, mobility models
and channel conditions. The goal of this section is to demonstrate that the Network Simulator
produces results that are consistent with those expectations, providing insight into the
performance of the network simulator and helping determine how scalable the network simulator
is.


### 4.1 Testing Methodology................................................................................................

Each experiment involved a variation of the following parameters

- Drones count: 5, 25, 100
- Routing protocol: AODV or OLSR
- Mobility model: Leader-Follower, Random Walk, Random Waypoint
- Channel: Ideal or probabilistic
- Transmission power: Low, Medium, High
- Simulation time: varies depending on routing stabilization
- Packet type: fixed or random source
- Evaluation metrics:
    - Packet Delivery Ratio (PDR)
    - End-to-End delay
    - MAC collision count
    - Routing load (AKA control overhead)
    - Throughput
    - Energy Consumption

### 4.2 Testing Mobility vs Latency.....................................................................................

4.2.1 Scenario 1: Leader-Follower with AODV

With 5 drones:
Resulted in PDR ~ 89% and a latency of ~ 520 ms with few collisions of 46 and stable

connectivity.


With 25 drones:
Resulted in PDR ~ 30% and a latency of ~ 6900 ms with routing load ~9.8 and 1700+
collisions.

With 100 drones:
Resulted in PDR ~ 6-7% and a latency of ~ 4500 ms with few collisions of 62K and Routing
load of 50


4.2.2 Testing Scenario 2: Leader-Follower with OLSR

With 5 drones:
Resulted in PDR ~ 99% and a latency of ~ 277 ms with routing load ~0.79 and 40 collisions.

With 25 drones:
Resulted in PDR ~34% and a latency of ~ 7880 ms with routing load ~2.70 and 2250+
collisions.


With 100 drones:172K and Routing load of 16.

4.2.3 Scenario 3: Random Waypoint with AODV

With 5 drones:

Resulted in PDR ~ 58% and a latency of ~ 1300 ms with routing load ~14 and 52 collisions.


With 25 drones:

Resulted in PDR ~ 13-14% and a latency of ~ 5500 ms with routing load ~38 and 2300

collisions.

With 100 drones:


Resulted in PDR ~ 3.7% and a latency of ~ 8000 ms with routing load ~116 and 113K

collisions.

Evidence from the evaluation suggests that a key factor of network performance is the mobility
structure. With the Leader-Follower model, the drones maintain predictable formations. The
result is that stable links are created and routing disruptions are minimalised, thus the routing
protocols can perform efficiently. Conversely, with the Random Waypoint model, links are
continuously severed due to the unpredictable movement patterns of the nodes. The result is
frequent flooding of the AODV routing protocol and severe routing instability. The scalability
testing results also indicate that while both models are impacted negatively as node count
increases, they fail for different reasons: whilst the Leader-Follower model fails primarily due to
MAC contention at high density, the Random Waypoint model fails as a result of a combination
of route churn caused by movement and increased contention. The latency behaviour is similar:
for the Leader-Follower model, most of the latency is caused by queue build-up, while for the
Random Waypoint model, much of the latency is due to the repeated retransmissions during the
route discovery process and queue overflow. Collision behaviours differ significantly: collisions
in the Leader-Follower model increase almost linearly with density, whereas in the Random
Waypoint model, they increase exponentially with density, due to the increased number of
control packets needed as a result of frequently severed routes. Overall, at every tested scale, the
Leader-Follower mobility structure out-performs the Random Waypoint mobility structure
because the Leader-Follower model maintains connectivity, has minimal routing instability, and
requires less control overhead than the Random Waypoint model.


### 4.3 Energy.....................................................................................................................

4.3.1 Throughput tradeoff: TX power levels vs lifetime/PDR

Tested with four drones:

```
TX Power PDR % Avg Delay (ms) Throughput
(kbps)
```
```
Collisions Final Energy
```
```
Low 98.49 95.79 573.72 26 123124.
```
```
Medium 97.99 103.39 507.84 21 123124.
```
```
High 99.83 91.65 532.92 13 123124.
```
Experiments performed to investigate three different modes of transmission power reveal
that the reliability remained very high with each mode set above a PDR rate of 97%. The

mode supplying high power delivered the highest PDR at approximately 99.8%.
However, the improvement compared with the modes supplying low and medium power
were fairly small, since the very reliable performance of the four-node topology produced
a high probability of delivery. For the parameters of end-to-end delay and throughput, the
mode supplying the higher power produced only a modest benefit by reducing end-to-end

delay from an average of 96-103 ms at low and medium transmission power levels down
to approximately 91 ms for the higher power level. At the same time, throughput levels
were relatively constant at around 500-570 Kbps for all three modes of transmission
power. Medium power had the highest average end-to-end delay and the lowest average
throughput when compared with other modes of transmission power. This was an

indicator that the link was less robust and there was slightly more contention when using
medium power versus higher transmission power configurations. The expected trend
regarding the number of collisions occurred as anticipated; the average number of
collisions per packet decreased as transmission power increased from low to high levels
of transmission power: average of 26 collisions during low power vs. 21 collisions during
medium power vs. 13 collisions for high power transmission. In a four-node topology,

increased transmission power enhances the quality of the received signal and improves
the SNR associated with the original transmitted signal. This results in reduced numbers
of retransmissions and enhanced MAC-layer performance even though the
communication range was increased.


Results from the energy consumption analysis indicate that all transmissions across low,

medium and high power settings used up to the same amount of energy at the end of the
30-second test. Since this test lasted such a short period, the energy consumed to send and
receive packets only represents a very small percentage of the original battery/energy
levels available on the drone. There was essentially no difference in total energy used
during the test due to deploying transmission power from 5 dBm to 20 dBm. Therefore,
for short time periods, with few packets being transmitted, the overall effect of changing

the effective transmission power on the lifetime of a node is negligible.

4.3.2 : AODV vs. OLSR

OLSR and AODV exhibit excellent performance within smaller areas which contain five
drones. OLSR enables route stability across all nodes throughout the network due to its
proactive link-state update mechanism, while AODV supports reduced per-packet latency

because of the lack of control messages required for transmission of low-volume traffic.
When extending the drone footprint to twenty-five, both routing protocols start seeing
degradation; however, AODV performs significantly better than OLSR related to
congestion control. OLSR specifically undergoes an increase in MAC contention due to
the implementation of periodic control floods, which will only increase as the

environment becomes denser. OLSR fails first at a total of one hundred drones because of
exponential growth with regards to routing table overhead and channel congestion,
ultimately resulting in severe collision cascades. AODV fails at this same number of total
drones due to being inundated with broadcast storms of RREQ messages and
overwhelming router queues caused by rapid changes in link state due to mobile nodes.

Overall, AODV demonstrated a more resilient routing protocol for use in high mobility
UAV networks, while OLSR was found to be useful only in small-stable environments
for ten or fewer drones because of its proactive routing capabilities.

The experiments showed that increasing transmission power will increase the reliability
and reduce the latency slightly but will not significantly impact the overall energy usage

of a drone network with a maximum distance between nodes of approximately 10m and a
very short (30 second) duration. For short missions with few nodes, using a transmission
power mode that is greater than the minimum recommended or "safe" level is a good
practice since it will provide a high level of reliability and not negatively impact the
overall battery life of the drone network; however, in larger networks or longer missions,

the energy-throughput tradeoff will be much greater than what was experienced for this
smaller experiment.


### 4.4 Formation Transition..............................................................................................

Testing with five drones:

Before the Switch (t ≈ 13s): At the prior to formation change, all drones' connections are
established. There was no packet loss (PDR = 100%); both latency and jitter levels were
maintained at acceptable limits, while transmission queues were rarely used, thus
indicating that the network has now converged and that routing has reached a point of

stability and balance in operations.

During the Switch (t = 15s):
Drones begin to relocate after the topology is altered, thus causing the existing network
links (connections) to break. AODV will react by transmitting new route requests


(RREQ) and route responses (RREP) through the network, thus increasing the control
overhead on the entire network yet again. The result of these activities will be a

short-term decrease in PDR (packet delivery ratio) to 0.98. Additionally, the latency will
increase to approximately 124 milliseconds (ms), and there will be an increase in jitter as
well as a queue for the packets that are waiting to be delivered via the newly formed
pathways. These types of changes in operating characteristics are not unexpected
following abrupt topology changes because the routing protocol must take time to
re-establish stable routes.

After the Switch (t = 20s): Subsequent to establishing their new formation, the routing
protocol for the drones stabilises once again but network performance does not return to a
state equivalent with pre-transition network performance levels. The PDR has decreased
to a value of 0.93; however, the latency and jitter are both increasing. Queue sizes also
remain higher than normal, indicating that there is still temporary congestion and that

there are still routes being recovered from this transition. The above result indicates that
formation switching has a substantial and ongoing effect on routing performance of
AODV, in the context of mobility, even when the topology has returned to a state of
stability.


## 5. Statement of Work........................................................................................................

Since the project is clearly outlined through network layers, the delegation of tasks was

pretty easy to implement. All members participated in the research of the topic. The
physical layer was implemented by Andrew Santos and Alyssa Serrano, the MAC layer
by Sergio Fernandez Donneys and Evan Tardiff, and the Routing and Networking by
Afnan Algharbi, Halie Do, and Jahnavi Panchal. The Mobility layer as well as topology,
GUI and Visualization were a collaboration between Cristian Carino and Reinier

Bondoc.The testing was done by Jahnavi Panchal. Additionally there were miscellaneous
tasks that took place such as team management and documentation as well as this
document which was done by Afnan Algharbi and Alyssa Serrano. Even though tasks
were divided, we all collaborated together when separate layers needed extra aid and met
weekly to discuss progress.

## 6. Conclusion References...................................................................................................

Ultimately, this Network Simulator offers a highly flexible and modular platform to
explore the communication, routing, mobility, and performance of multiple drones

working together over a shared wireless network. As a result of this flexibility, users can


easily configure and experiment with different types of protocols, mobility models, and
channel conditions while accessing the same visual representation and performance

metrics to assist with their analysis. The testing and evaluation of the Network Simulator
indicates that it has the ability to produce realistic behaviours for drones operating in
varying types of networks across different scenarios and scales. Therefore, it has great
potential for future research, education, and development related to multi-drone
communication and can provide a robust research tool for those working on developing
multipoint wireless networks. In addition, because the Network Simulator is based upon

an extensible framework, it has the capacity to continue to develop as new technologies
and networking concerns arise.


References
[1] Z. Zhou _et al_ ., “UavNetSim-v1: A Python based Simulation Platform for UAV
Communication Networks,” GitHub. Accessed: Dec. 6, 2025. [Online]. Available:
https://github.com/Zihao-Felix-Zhou/UavNetSim-v1

GitHub

[2] “Review of IEEE-802.11n,” _Linux Wireless documentation_. Accessed: Dec. 6, 2025.
[Online]. Available:
https://wireless.docs.kernel.org/en/latest/en/developers/documentation/ieee80211/802.11n.html

Linux Wireless Documentation

[3] Cisco Systems, “802.11ac MCS rates,” _Cisco Support Community_. Accessed: Dec. 6, 2025.
[Online]. Available:
https://community.cisco.com/t5/wireless-mobility-knowledge-base/802-11ac-mcs-rates/ta-p/3155
920


