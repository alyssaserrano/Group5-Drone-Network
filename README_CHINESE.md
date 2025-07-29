<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/logo.png" width="650px">
</div>

<div align="center">
  <h1>UavNetSim-v1: 基于Python的无人机通信网络仿真平台</h1>

  <img src="https://img.shields.io/badge/Github-%40Zihao--Felix--Zhou-blue" height="20">
  <img src="https://img.shields.io/badge/License-MIT-brightgreen" height="20">
  <img src="https://img.shields.io/badge/Version-V1.0-orange" height="20">
  <img src="https://img.shields.io/badge/Contributions-Welcome-yellowgreen" height="20">
 

  <h3>让仿真对新手更友好! </h3>
</div>

以其他语言阅读此文档: [English](README.md)  

这一款基于Python的仿真平台能够对无人机网络中的多个组件进行真实且完整的建模，包括网络层、媒体接入控制层、物理层，以及无人机移动模型和能量模型。此外，该平台极易扩展，便于用户定制及开发不同的协议以适应不同的应用需求。 <br>

该项目对应于下方所示的论文，除此之外，我们近期也新增了许多新的模块以及baselines。<br>

> **[UavNetSim-v1: A Python-based Simulation Platform for UAV Communication Networks](https://arxiv.org/abs/2507.09852)** <br>
> [Zihao Zhou](https://zihao-felix-zhou.github.io/)<sup>1</sup>, [Zipeng Dai](http://zipengdai.com/)<sup>2</sup>, Linyi Huang<sup>3</sup>, [Cui Yang](https://yanzhao.scut.edu.cn/open/ExpertInfo.aspx?zjbh=YBh67JO2Lu3MRcgZBW!y0g==)<sup>1</sup>, [Youjun Xiang](https://yanzhao.scut.edu.cn/open/ExpertInfo.aspx?zjbh=OqvoZ7Uc98hlRMLm8c2JGA==)<sup>1</sup>, [Jie Tang](https://yanzhao.scut.edu.cn/open/ExpertInfo.aspx?zjbh=jAxeXRUecjTAjkxrmc2Dnw==)<sup>1</sup> and [Kai-kit Wong](https://www.ee.ucl.ac.uk/~uceekwo/)<sup>4,5</sup> <br>
> <sup>1</sup> School of Electronic and Information Engineering, South China University of Technology <br>
> <sup>2</sup> Department of Computer Science and Technology, Beijing Institute of Technology <br>
> <sup>3</sup> Thrust of ROAS, The Hong Kong University of Science and Technology (Guangzhou) <br>
> <sup>4</sup> Department of Electrical and Electronic Engineering, University College London <br>
> <sup>5</sup> Yonsei Frontier Lab, Yonsei University

<div align="center">
<img src="https://github.com/Zihao-Felix-Zhou/UavNetSim-v1/blob/master/img/Schematic_of_uav_swarms.png" width="1000px">
</div>

## 依赖
- matplotlib==3.10.1
- numpy==2.2.4
- openpyxl==3.1.5
- Pillow==11.2.1
- scikit_opt==0.6.6
- simpy==4.1.1

## 特色
在开始您的仿真之旅前，我们建议您先阅读本小节，本节中介绍了该平台的一些特点，您可以据此来判断该平台是否满足您的开发或研究需求。
- 该平台完全基于Python开发（主要是基于Python中的SimPy库）；
- 更加适合对**路由协议**、**MAC协议**以及**移动控制算法**（如：**拓扑控制**、**轨迹优化**）的开发与验证。未来我们希望能够进一步扩展该平台以支持更多不同层的算法与协议；
- 支持**强化学习**以及其他基于AI的算法；
- 易于扩展（1.采用**模块化编程方案**，因此用户可以很轻易地增加自己设计的模块；2. 潜在地支持不同的应用场景，如**飞行自组织网络**，**无人机辅助的数据采集**，**空地一体化网络**等）；
- **较好的可视化**，该平台能够直观地展示无人机的**飞行轨迹**以及**包的传输路径**，这能够帮助用户直观地分析协议的行为；
- 如果您从事无人机辅助的无线通信系统，并希望能够考虑更多**跨层指标**（如端到端时延、包传输率，吞吐量等），那么这款平台将会适合你！

## 项目架构

```
.
├── README.md
├── allocation
│   ├── central_controller.py
│   └── channel_assignment.py
├── energy
│   └── energy_model.py
├── entities
│   ├── drone.py
│   ├── obstacle.py
│   └── packet.py
├── mac
│   ├── csma_ca.py
│   └── pure_aloha.py
├── mobility
│   ├── gauss_markov_3d.py
│   ├── random_walk_3d.py
│   ├── random_waypoint_3d.py
│   └── start_coords.py
├── path_planning
│   ├── astar
│   │   └── astar.py
├── phy
│   ├── channel.py
│   ├── large_scale_fading.py
│   └── phy.py
├── routing
│   ├── dsdv
│   │   ├── dsdv.py
│   │   ├── dsdv_packet.py
│   │   └── dsdv_routing_table.py
│   ├── grad
│   │   └── ...
│   ├── greedy
│   │   └── ...
│   ├── opar
│   │   └── ...
│   └── q_routing
│       └── ...
├── simulator
│   ├── metrics.py
│   └── simulator.py
├── topology
│   └── virtual_force
│       ├── vf_motion_control.py
│       ├── vf_neighbor_table.py
│       └── vf_packet.py
├── utils
│   ├── config.py
│   ├── ieee_802_11.py
│   └── util_function.py
├── visualization
│   ├── static_drawing.py
│   └── visualizer.py
└── main.py
```
该项目的入口是```main.py```文件，我们甚至可以直接一键运行来提前预览一下效果，但我们还是建议您先阅读本节，了解该仿真平台的模块组成和相应的功能。

- ```allocation```:该文件夹中包括了不同的资源分配算法模块，例如：子信道分配策略。未来可以考虑进一步实现功率分配算法。
- ```energy```: 该文件夹中包括了无人机的能量消耗模型，包括飞行以及通信相关的能量消耗。
- ```entities```: 它包含与仿真中涉及的主要实体相对应的所有模块。
- ```mac```: 其包含了不同媒体接入控制协议的实现。
- ```mobility```: 其包含了不同的无人机三维移动模型。
- ```path_planning```: 其包含了不同的无人机三维路径规划算法模块（如A*算法）。
- ```phy```: 其主要包括了物理层无线信道的建模，以及对单播、多播和广播行为的定义。
- ```routing```: 其主要包括了不同路由协议的实现。
- ```simulator```: 其包含了进行仿真和评估网络性能指标所需的所有类。
- ```topology```: 其包含了不同的无人机集群拓扑控制算法的实现。
- ```utils```: 其包含了关键的仿真参数设置以及一些常用的函数。
- ```visualization```: 能够提供无人机节点分布、飞行轨迹和数据包转发路径的可视化展示。

| 层 | 当前已经实现的协议、算法或模型 |
| --- | --- |
| 应用层 | 服从均匀分布的数据包达到 <br> 服从泊松分布的数据包到达 |
| 传输层 | Automatic repeat request (ARQ) |
| 网络层 | 路由协议: <br> <ul><li>[DSDV: Destination-Sequenced Distance-Vector routing](https://dl.acm.org/doi/abs/10.1145/190809.190336)</li> <li>[GRAd: Gradient Routing in Ad Hoc Networks](www.media.mit.edu/pia/Research/ESP/texts/poorieeepaper.pdf)</li> <li>[Greedy forwarding](https://en.wikipedia.org/wiki/Geographic_routing)</li> <li>[OPAR: Optimized Predictive and Adaptive Routing](https://ieeexplore.ieee.org/abstract/document/9484489)</li> <li>[QMR: Q-learning based Multi-objective optimization Routing](https://hal.science/hal-02970649v1/document)</li> <li>[QGeo: Q-learning-based Geographic routing](https://ieeexplore.ieee.org/abstract/document/7829268/)</li> <li>[Classical Q-Routing](https://proceedings.neurips.cc/paper/1993/hash/4ea06fbc83cdd0a06020c35d50e1e89a-Abstract.html)</li></ul>|
| 拓扑控制层 | 随机移动模型: <br> <ul><li>[3D Gauss-Markov mobility model](https://repository.arizona.edu/bitstream/handle/10150/604297/ITC_2010_10-03-06.pdf?sequence=1&isAllowed=y)</li><li>[3D Random Waypoint mobility model](https://ieeexplore.ieee.org/document/8671460)</li><li>[3D Random Walk mobility model](https://link.springer.com/chapter/10.1007/978-1-4419-6050-4_3#citeas)</li></ul> 拓扑控制算法: <br> <ul><li>[Virtual force-based topology control](https://ieeexplore.ieee.org/document/5555924)</li></ul> 路径规划以及避障算法: <br> <ul><li>A* 3D path planning</li></ul>|
| 媒体接入控制层 |<ul><li>[CSMA/CA: Carrier-Sense Multiple Access with Collision Avoidance](https://en.wikipedia.org/wiki/Carrier-sense_multiple_access_with_collision_avoidance)</li> <li>[Pure ALOHA](https://www.tutorialspoint.com/data_communication_computer_network/pure_aloha.htm)</li></ul>|
| 物理层 | 所考虑的物理层特性: <br> <ul><li>视距信道</li> <li>概率视距信道</li> <li>数据包碰撞以及信号干扰</li> <li>单播、多播以及广播</li></ul> |

## 安装及使用
首先，下载该项目:
```
git clone https://github.com/Zihao-Felix-Zhou/UavNetSim-v1.git
```
运行 ```main.py``` 以启动仿真. 
