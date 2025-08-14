## 最终目标
你的最终目标是当我设置data的路径时，能将我目前提供的'data_dir\background'中的信息都能自动读取并且正确进行设置。

## 涉及的背景数据

项目中涉及的背景数据如下：

### books

项目中主要涉及两种books, 在lifelongagentbench中由LifelongAgentBench-main\src\tasks\instance\campus_life_bench\system_prompt_generator.py文件中进行声明，在data_dir\background\books.json文件中进行存储
1. 学生手册和学术规范手册，以及培养方案，在系统中应该由“学生手册”和“学术规范”和“培养方案”三个json提供。后续你可以根据需要将其合并为一个文件。
2. 课本。本评测主要包含8个课本，在data_dir\background\books\中分为8个json进行提供。后续你可以根据需要将其合并为一个文件。

这些所有的books都满足chapter-section-article的层级结构。books的特点是可以直接获取到原文。



### 校园信息
校园信息主要包含以下几类
1. 地图，在data_dir\background\map_v1.5.json文件中进行存储。
2. 导师列表，在data_dir\background\advisor.json文件中进行存储。
3. 图书馆座位地图，在data_dir\background\lib_map_with_seats.json文件中进行存储。 
4. 社团列表，在data_dir\background\student_clubs.json文件中进行存储。
5. 图书馆内馆藏列表，在data_dir\background\lib_books_database.json文件中进行存储。


## 你的任务

### 任务一：检查lifelongagentbench的campustask类是如何读取这些信息的

你需要检查lifelongagentbench的campustask类是如何读取这些信息的。如果有信息无法被读取，则需要对应进行添加和修改

### 任务二：给出一套规范的基于data_dir\background中的信息，进行设置的方案

你需要给出需要提供什么样的文件，以及具体的要求

### 任务三：更改当前读取方法和本地文件合并

你需要按照方案对应更改当前系统中的实现，从而实现鲁棒的读取

同时，相应的根据方案，对任务数据\background下的数据进行整合、更名等操作，以符合需求。注意，对于处理完后的数据，内部应该是全英文的。


### 任务四: 优化对背景数据声明的prompt

优化我在LifelongAgentBench-main\src\tasks\instance\campus_life_bench\system_prompt_generator.py文件中对这两类信息的声明，给出具体的书目名称和列表，以便Agent使用工具进行查询。


### 任务五：生成readme
在data_dir\background下生成一个readme.md文件，用于说明当前背景数据的内容和结构。