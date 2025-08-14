# CampusLifeBench 测试目录结构

本目录包含CampusLifeBench项目的所有测试文件，按照功能和类型进行分类组织。

## 目录结构

```
tests/
├── README.md                    # 本文件，说明测试目录结构
├── campus_life_bench/          # CampusLifeBench核心测试
│   ├── unit_tests/             # 单元测试
│   ├── integration_tests/      # 集成测试
│   ├── e2e_tests/             # 端到端测试
│   ├── test_data/             # 测试数据文件
│   ├── test_results/          # 测试结果输出
│   └── test_output/           # 测试输出文件
├── action_system/              # Action系统相关测试
├── parsing_tests/              # 解析功能测试
├── validation_tests/           # 验证测试
└── reports/                    # 测试报告和文档
```

## 测试类型说明

### 单元测试 (unit_tests/)
- 测试单个系统组件的功能
- 包括各个子系统的独立测试
- 文件命名格式：`test_<system_name>.py`

### 集成测试 (integration_tests/)
- 测试多个系统之间的交互
- 验证系统间数据传递和状态同步
- 文件命名格式：`integration_test_<scenario>.py`

### 端到端测试 (e2e_tests/)
- 完整的用户场景测试
- 跨天模拟和长期状态持久化测试
- 文件命名格式：`e2e_test_<scenario>.py`

### 测试数据 (test_data/)
- JSON格式的测试数据文件
- 包含各种测试场景的输入数据
- 按系统和场景分类存放

### 测试结果 (test_results/)
- 测试执行结果的JSON报告
- 性能指标和验证结果
- 按日期和测试类型分类存放

## 运行测试

### 运行所有测试
```bash
python -m pytest tests/ -v
```

### 运行特定类型的测试
```bash
# 单元测试
python -m pytest tests/campus_life_bench/unit_tests/ -v

# 集成测试
python -m pytest tests/campus_life_bench/integration_tests/ -v

# 端到端测试
python -m pytest tests/campus_life_bench/e2e_tests/ -v
```

### 运行特定测试文件
```bash
python tests/campus_life_bench/unit_tests/test_course_selection.py
```

## 测试数据格式

所有测试数据文件应使用JSON格式，并包含以下标准字段：
- `test_name`: 测试名称
- `description`: 测试描述
- `input_data`: 输入数据
- `expected_output`: 期望输出
- `validation_criteria`: 验证标准

## 注意事项

1. 所有测试输出必须使用英文，确保与CampusLifeBench的语言要求一致
2. 测试数据文件应包含充分的边界情况和异常场景
3. 集成测试应验证状态持久化和跨系统数据一致性
4. 端到端测试应模拟真实的用户使用场景
