# 自定义 Campus Life Bench 任务配置文件说明

本目录下的 `campus_life_bench_custom.yaml` 文件用于运行 `CampusTask`，并加载自定义的任务数据。

## 配置文件：`campus_life_bench_custom.yaml`

此文件是基于 `LifelongAgentBench-main/configs/assignments/examples/deepseek_chat/instance/campus_life_bench/instance/campus_life_bench_deepseek.yaml` 修改而来，主要区别在于它加载的是 `任务数据/task_complete.json` 中定义的任务。

### 如何使用

要运行此配置，请使用以下命令：

```bash
$env:PYTHONPATH="." ; python src/run_experiment.py --config_path 任务数据/config/campus_life_bench_custom.yaml
```

**注意**：在运行前，请确保将 `campus_life_bench_custom.yaml` 文件中的 `YOUR_API_KEY` 替换为您自己的 DeepSeek API 密钥。

### 参数详解

以下是 `campus_life_bench_custom.yaml` 中关键参数的说明：

-   `language_model_dict`: 定义了所使用的语言模型。
    -   `deepseek-chat`: 模型的名称。
        -   `module`: 指定了语言模型的实现类。
        -   `parameters`:
            -   `model_name`: 模型的具体名称。
            -   `api_key`: **（需要修改）** DeepSeek 的 API 密钥。
            -   `base_url`: API 的基地址。

-   `agent_dict`: 定义了代理（Agent）。
    -   `language_model_agent`: 代理的名称。
        -   `module`: 代理的实现类。
        -   `parameters`:
            -   `language_model`: 指定了该代理使用的语言模型。`"Fill the parameter 'language_model_name' in assignment config."` 是一个占位符，实际值会在 `assignment_config` 中指定。

-   `task_dict`: 定义了任务。
    -   `campus_life_bench`: 任务的名称。
        -   `module`: 任务的实现类，这里是 `src.tasks.instance.campus_life_bench.task.CampusTask`。
        -   `parameters`:
            -   `task_name`: 任务的名称。
            -   `chat_history_item_factory`: 用于创建聊天历史记录项的工厂。
            -   `max_round`: 任务的最大交互轮次。
            -   `data_dir`: **（核心修改）** 指定了任务数据的加载目录。在这里，它指向 `任务数据/custom_task_data`。`CampusTask` 会从此目录下的 `tasks.json` 文件加载任务，而该文件是我们从 `任务数据/task_complete.json` 复制而来的。

-   `assignment_config`: 将上述定义的语言模型、代理和任务组装在一起。
    -   `language_model_list`: 指定了要使用的语言模型列表。
    -   `agent`: 指定了要使用的代理。
    -   `task`: 指定了要运行的任务。
    -   `output_dir`: 指定了实验结果的输出目录。`{TIMESTAMP}` 会被替换为当前的时间戳。

-   `environment_config`: 环境配置。
    -   `use_task_client_flag`: 是否使用任务客户端。

-   `logger_config`: 日志配置。
    -   `level`: 日志级别（例如 `INFO`, `DEBUG`）。
    -   `logger_name`: 日志记录器的名称。
