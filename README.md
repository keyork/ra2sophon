# ra2sophon

Red Alert 2: Yuri's Revenge 的游戏状态读取工具。通过读取游戏进程内存获取实时状态信息（资金、电力、单位、建筑等），为 AI 代理提供感知基础。

## 功能

- 从运行中的游戏进程读取资金、电力、建筑数量、单位数量
- 按类型细分的单位/建筑统计（精确到每种单位各有多少）
- 双方阵营状态同时监控
- 游戏关闭/重启后自动重连
- 交互式内存偏移探针，用于发现新的内存地址
- 堆扫描器，查找玩家拥有的单位与建筑对象

## 前置条件

- Windows 操作系统（依赖 ReadProcessMemory）
- Python 3.11+
- Red Alert 2: Yuri's Revenge（CnCNet 版，进程名 gamemd-spawn.exe）
- 以管理员权限运行（进程内存访问需要提权）

## 安装

```bash
uv sync
```

依赖项：
- [pymem](https://pypi.org/project/pymem/) -- 进程内存读取

## 使用

所有命令通过 `uv run` 执行：

```bash
# 读取并打印一次游戏状态
uv run python -m ra2sophon

# 持续监控，每秒刷新，游戏关闭后自动重连
uv run python -m ra2sophon monitor

# 交互式内存偏移探测，用于发现新的数据地址
uv run python -m ra2sophon probe

# 扫描玩家拥有的单位与建筑对象
uv run python -m ra2sophon objects

# 按类型显示各方阵营的单位/建筑明细
uv run python -m ra2sophon stats
```

## 项目结构

```
ra2sophon/
├── pyproject.toml
└── src/ra2sophon/
    ├── __init__.py              # 包导出
    ├── __main__.py              # python -m 入口
    ├── memory/                  # 内存读取层
    │   ├── offsets.py           # RA2 内存偏移常量
    │   ├── types.py             # 数据类（GameState, HouseInfo, TypeCount 等）
    │   ├── reader.py            # GameReader + TypeRegistry（核心内存读取器）
    │   └── objects.py           # 堆对象扫描器（查找玩家单位/建筑）
    ├── display/                 # 终端显示层
    │   └── format.py            # 格式化输出函数
    └── cli/                     # 命令行界面
        ├── main.py              # 入口（state, probe, monitor, objects, stats）
        ├── monitor.py           # 持续监控，带自动重连
        └── probe.py             # 交互式内存偏移发现工具
```

## 架构概览

项目分两层，各层职责明确：

```
┌─────────────────────────────────────────────┐
│                  CLI 层                      │
│  main.py / monitor.py / probe.py            │
│  命令解析、模式切换、输出展示                  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
         ┌───────────────────┐
         │     memory/       │
         │     内存读取层     │
         │                   │
         │  GameReader       │
         │  TypeRegistry     │
         │  堆扫描器          │
         └─────────┬─────────┘
                   │
                   ▼
          pymem 读取进程内存
```

- **memory 层**：通过 pymem 附加到游戏进程，按预定义偏移量读取 HouseClass 结构体，解析出资金、电力、各单位数量等数据。TypeRegistry 维护单位类型名到索引的映射。堆扫描器遍历游戏堆内存定位玩家对象。
- **display 层**：将 GameState 格式化为终端可读文本。

## 许可证

Apache License 2.0
