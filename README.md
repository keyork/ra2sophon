# ra2sophon

Red Alert 2: Yuri's Revenge 实时战场信息读取工具。通过读取游戏进程内存，获取双方阵营的详细战场状态——资金、电力、每种单位各有多少、建筑明细，全部中文显示。

![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)
![Windows](https://img.shields.io/badge/Platform-Windows-orange)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

## 功能

- **按类型统计** — 精确到每种单位/建筑各有多少（如：灰熊坦克 x5、光棱塔 x3）
- **五类分册** — 建筑、步兵、载具、海军、飞机分别统计
- **中文显示** — 127 种单位全部中文名称
- **浮窗 Overlay** — 游戏内半透明浮窗，F9 切换显示/隐藏
- **自动检测** — 先开工具再开游戏，进入对战后自动连接；游戏关闭后自动重连
- **双方监控** — 同时显示己方和对方阵营状态
- **交互式探针** — 用于发现新的内存地址
- **堆扫描器** — 查找玩家拥有的单位与建筑对象

## 前置条件

- Windows 操作系统（依赖 ReadProcessMemory）
- Python 3.11+
- Red Alert 2: Yuri's Revenge（CnCNet 版，进程名 `gamemd-spawn.exe`）
- **管理员权限**运行终端（进程内存访问需要提权）

## 安装

```bash
git clone https://github.com/keyork/ra2sophon.git
cd ra2sophon
uv sync
```

依赖项：
- [pymem](https://pypi.org/project/pymem/) — 进程内存读取
- [pydirectinput](https://pypi.org/project/pydirectinput/) — 输入模拟

## 使用

所有命令以管理员权限运行：

```bash
# 浮窗模式 — 游戏内半透明 Overlay，F9 切换显示/隐藏
uv run python -m ra2sophon overlay

# 终端统计 — 打印一次各方阵营的详细单位明细
uv run python -m ra2sophon stats

# 持续监控 — 终端每秒刷新，游戏关闭后自动重连
uv run python -m ra2sophon monitor

# 读取一次完整游戏状态
uv run python -m ra2sophon

# 交互式内存偏移探测
uv run python -m ra2sophon probe

# 扫描玩家拥有的单位与建筑对象
uv run python -m ra2sophon objects
```

### 浮窗模式

```bash
uv run python -m ra2sophon overlay
```

特性：
- 始终置顶，半透明深色背景
- 左上角显示，不遮挡游戏操作
- **F9** 全局热键切换显示/隐藏
- 每秒自动刷新数据
- 先开浮窗再开游戏，进入对战后自动连接

外观可通过 `src/ra2sophon/data/overlay.toml` 自定义。

### 修改金钱

```bash
# 给自己加 50000 块（累加，不是覆盖）
uv run python -m ra2sophon money 50000

# 给所有人加
uv run python -m ra2sophon money 50000 --all
```

> ⚠ **WARNING: 请勿用于 CnCNet 在线对战，仅限单机/Skirmish 使用。**

## 配置文件

### 浮窗外观 — `data/overlay.toml`

```toml
[overlay]
alpha = 0.90                # 窗口透明度 (0.3 - 1.0)
position = "+10+10"         # 屏幕位置
line_width = 50             # 每行最大字符数

[colors.faction]
allied = "#4fc3f7"          # 盟军蓝色
soviet = "#ef5350"          # 苏军红色
yuri = "#ab47bc"            # 尤里紫色

[fonts]
header = ["Consolas", 10, "bold"]
body = ["Consolas", 9]
```

修改后重启浮窗即可生效。

### 单位定义 — `data/unitdefs.json`

127 种单位的中英文名称、内存偏移量、阵营、类别等。格式：

```json
{"name": "Grizzly Battle Tank", "name_cn": "灰熊坦克", "offset": "0x024", "index": 3, "category": "vehicle", "faction": "allied"}
```

数据来源于 [ra2ob](https://github.com/wudi-7mi/ra2ob) 的 `unit_offsets.json`。

## 项目结构

```
ra2sophon/
├── pyproject.toml
└── src/ra2sophon/
    ├── __init__.py
    ├── __main__.py
    ├── data/                        # 配置文件（非代码）
    │   ├── unitdefs.json            # 127 种单位定义
    │   └── overlay.toml             # 浮窗外观配置
    ├── memory/                      # 内存读取层
    │   ├── offsets.py               # RA2 内存偏移常量
    │   ├── types.py                 # 数据类（GameState, HouseInfo, TypeCount）
    │   ├── reader.py                # GameReader 核心内存读取器
    │   ├── unitdefs.py              # JSON 加载 + 查找索引
    │   └── objects.py               # 堆对象扫描器
    ├── display/
    │   └── format.py                # 终端格式化输出
    └── cli/
        ├── main.py                  # CLI 入口
        ├── overlay.py               # 浮窗 Overlay（tkinter）
        ├── monitor.py               # 终端持续监控
        └── probe.py                 # 交互式内存偏移探针
```

## 内存读取原理

```
gamemd-spawn.exe
  └─ HouseClass (每个玩家一个)
       ├─ Credits, Power, Defeated 等字段
       └─ 4 个 CounterClass (建筑/载具/步兵/飞机)
            └─ Items[int] — 每种类型的存活数量
```

偏移量来自 [YRpp](https://github.com/Metadorius/YRpp)（C++ 头文件）和 [ra2ob](https://github.com/wudi-7mi/ra2ob)（offset 常量）。

建筑类型名通过堆扫描 `BuildingTypeClass` 的 vtable 签名发现；其他类型通过 `DynamicVectorClass` 数组读取。

## 致谢

- [ra2ob](https://github.com/wudi-7mi/ra2ob) — 内存偏移常量和单位偏移表
- [YRpp](https://github.com/Metadorius/YRpp) — YR C++ 头文件（结构体定义）
- [ra2viewer](https://github.com/chenguokai/ra2viewer) — 内存读取方法参考

## 许可证

Apache License 2.0
