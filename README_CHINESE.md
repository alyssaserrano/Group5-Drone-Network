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
