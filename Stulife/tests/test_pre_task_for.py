#!/usr/bin/env python3
"""
Test script for pre_task_for functionality
测试 pre_task_for 前置任务依赖功能
"""

import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
from src.typings import SessionEvaluationOutcome


def create_test_tasks():
    """创建测试用的任务数据"""
    return {
        "0_prerequisite_task": {
            "task_id": "prerequisite_task",
            "task_type": "email_sending",
            "is_trigger": False,
            "instruction": "发送一封邮件给导师",
            "require_time": None,
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [],
            "details": {
                "recipient": "advisor@university.edu",
                "subject": "Test Email",
                "body": "Test body"
            },
            "ground_truth": {
                "recipient": "advisor@university.edu",
                "subject": "Test Email",
                "body": "Test body"
            },
            "pre_task_for": "dependent_task_1,dependent_task_2",  # 注意：使用task_id而不是JSON key
            "available_systems": ["email"]
        },
        "1_dependent_task_1": {
            "task_id": "dependent_task_1",
            "task_type": "email_sending", 
            "is_trigger": False,
            "instruction": "发送另一封邮件",
            "require_time": None,
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [],
            "details": {
                "recipient": "student@university.edu",
                "subject": "Dependent Email 1",
                "body": "This task depends on prerequisite_task"
            },
            "ground_truth": {
                "recipient": "student@university.edu", 
                "subject": "Dependent Email 1",
                "body": "This task depends on prerequisite_task"
            },
            "available_systems": ["email"]
        },
        "2_dependent_task_2": {
            "task_id": "dependent_task_2",
            "task_type": "email_sending",
            "is_trigger": False,
            "instruction": "发送第三封邮件",
            "require_time": None,
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [],
            "details": {
                "recipient": "professor@university.edu",
                "subject": "Dependent Email 2", 
                "body": "This task also depends on prerequisite_task"
            },
            "ground_truth": {
                "recipient": "professor@university.edu",
                "subject": "Dependent Email 2",
                "body": "This task also depends on prerequisite_task"
            },
            "available_systems": ["email"]
        },
        "3_independent_task": {
            "task_id": "independent_task",
            "task_type": "email_sending",
            "is_trigger": False,
            "instruction": "发送独立邮件",
            "require_time": None,
            "require_place": None,
            "source_building_id": None,
            "world_state_change": [],
            "details": {
                "recipient": "friend@university.edu",
                "subject": "Independent Email",
                "body": "This task is independent"
            },
            "ground_truth": {
                "recipient": "friend@university.edu",
                "subject": "Independent Email", 
                "body": "This task is independent"
            },
            "available_systems": ["email"]
        }
    }


def create_mock_session():
    """创建模拟的Session对象"""
    session = Mock()
    session.evaluation_record = Mock()
    session.evaluation_record.outcome = None
    session.evaluation_record.detail_dict = None
    session.task_output = None
    session.chat_history = Mock()
    session.chat_history.get_item_deep_copy = Mock()
    session.chat_history.get_value_length = Mock(return_value=0)
    return session


def test_pre_task_for_functionality():
    """测试 pre_task_for 功能"""
    print("🧪 开始测试 pre_task_for 功能")
    
    # 创建临时目录和测试数据文件
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tasks_file = temp_path / "tasks.json"
        
        # 写入测试数据
        test_tasks = create_test_tasks()
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(test_tasks, f, indent=2, ensure_ascii=False)
        
        print(f"📁 创建测试数据文件: {tasks_file}")
        
        # 创建CampusTask实例（使用Mock对象替代ChatHistoryItemFactory）
        chat_factory = Mock()  # 我们不需要真正的ChatHistoryItemFactory来测试pre_task_for功能
        campus_task = CampusTask("campus_life_bench", chat_factory, max_round=5, data_dir=temp_path)
        
        print("✅ CampusTask 实例创建成功")
        
        # 测试1: 验证数据加载
        print("\n📋 测试1: 验证数据加载")
        dataset = campus_task._Task__dataset
        
        assert "0_prerequisite_task" in dataset
        assert "1_dependent_task_1" in dataset
        assert "2_dependent_task_2" in dataset
        assert "3_independent_task" in dataset
        
        prereq_item = dataset["0_prerequisite_task"]
        assert prereq_item.task_id == "prerequisite_task"  # 注意：task_id是字段值，不是key
        assert prereq_item.pre_task_for == "dependent_task_1,dependent_task_2"
        
        print("✅ 数据加载验证通过")
        
        # 测试2: 模拟前置任务失败
        print("\n📋 测试2: 模拟前置任务失败")
        campus_task._Task__current_dataset_item_index = "0_prerequisite_task"
        
        session1 = create_mock_session()
        session1.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
        
        # 调用完成方法，这应该记录失败的前置任务
        campus_task._complete(session1)
        
        # 验证失败前置任务被记录
        assert "prerequisite_task" in campus_task.failed_prerequisite_tasks
        affected_tasks = campus_task.failed_prerequisite_tasks["prerequisite_task"]
        assert "dependent_task_1" in affected_tasks
        assert "dependent_task_2" in affected_tasks
        
        print("✅ 前置任务失败记录成功")
        print(f"   - 失败任务: prerequisite_task")
        print(f"   - 受影响任务: {affected_tasks}")
        
        # 测试3: 验证受影响任务被标记为失败
        print("\n📋 测试3: 验证受影响任务被标记为失败")
        
        # 测试dependent_task_1
        campus_task._Task__current_dataset_item_index = "1_dependent_task_1"
        session2 = create_mock_session()
        
        campus_task._complete(session2)
        
        assert session2.evaluation_record.outcome == SessionEvaluationOutcome.INCORRECT
        assert session2.task_output == {"result": "Set to incorrect due to the pre task"}
        assert session2.evaluation_record.detail_dict["failed_due_to_prerequisite"] == True
        assert session2.evaluation_record.detail_dict["failed_prerequisite_task_id"] == "prerequisite_task"
        
        print("✅ dependent_task_1 正确标记为失败")
        print(f"   - 失败原因: {session2.evaluation_record.detail_dict['reason']}")
        
        # 测试dependent_task_2
        campus_task._Task__current_dataset_item_index = "2_dependent_task_2"
        session3 = create_mock_session()
        
        campus_task._complete(session3)
        
        assert session3.evaluation_record.outcome == SessionEvaluationOutcome.INCORRECT
        assert session3.task_output == {"result": "Set to incorrect due to the pre task"}
        
        print("✅ dependent_task_2 正确标记为失败")
        
        # 测试4: 验证独立任务不受影响
        print("\n📋 测试4: 验证独立任务不受影响")
        
        campus_task._Task__current_dataset_item_index = "3_independent_task"
        session4 = create_mock_session()
        
        # 手动设置一个评估结果，模拟正常评估流程
        session4.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT
        
        campus_task._complete(session4)
        
        # 独立任务应该保持其原有的评估结果
        assert session4.evaluation_record.outcome == SessionEvaluationOutcome.CORRECT
        
        print("✅ independent_task 不受前置任务失败影响")
        
        # 测试5: 验证辅助方法
        print("\n📋 测试5: 验证辅助方法")
        
        # 测试 _check_affected_by_failed_prerequisite
        assert campus_task._check_affected_by_failed_prerequisite("dependent_task_1") == "prerequisite_task"
        assert campus_task._check_affected_by_failed_prerequisite("dependent_task_2") == "prerequisite_task"
        assert campus_task._check_affected_by_failed_prerequisite("independent_task") is None
        
        print("✅ 辅助方法验证通过")
        
        print("\n🎉 所有测试通过！pre_task_for 功能工作正常")


def test_edge_cases():
    """测试边界情况"""
    print("\n🧪 测试边界情况")
    
    # 测试空的pre_task_for字段
    item1 = CampusDatasetItem(
        task_id="test1",
        task_type="email_sending",
        pre_task_for=""
    )
    
    item2 = CampusDatasetItem(
        task_id="test2", 
        task_type="email_sending",
        pre_task_for="   "  # 只有空格
    )
    
    item3 = CampusDatasetItem(
        task_id="test3",
        task_type="email_sending", 
        pre_task_for="task1, , task2,  task3 "  # 包含空值和多余空格
    )
    
    # 模拟记录失败前置任务
    campus_task = Mock()
    campus_task.failed_prerequisite_tasks = {}
    
    def mock_record_failed_prerequisite_task(session, current_item):
        """模拟_record_failed_prerequisite_task方法的逻辑"""
        if (session.evaluation_record.outcome == SessionEvaluationOutcome.INCORRECT and 
            current_item.pre_task_for is not None and 
            current_item.pre_task_for.strip() != ""):
            
            affected_task_ids = [task_id.strip() for task_id in current_item.pre_task_for.split(",") if task_id.strip()]
            
            if affected_task_ids:
                campus_task.failed_prerequisite_tasks[current_item.task_id] = affected_task_ids
    
    session = Mock()
    session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
    
    # 测试空字符串情况
    mock_record_failed_prerequisite_task(session, item1)
    assert "test1" not in campus_task.failed_prerequisite_tasks
    
    # 测试只有空格情况
    mock_record_failed_prerequisite_task(session, item2)
    assert "test2" not in campus_task.failed_prerequisite_tasks
    
    # 测试正常解析情况
    mock_record_failed_prerequisite_task(session, item3)
    assert "test3" in campus_task.failed_prerequisite_tasks
    assert campus_task.failed_prerequisite_tasks["test3"] == ["task1", "task2", "task3"]
    
    print("✅ 边界情况测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 pre_task_for 功能测试脚本")
    print("=" * 60)
    
    try:
        test_pre_task_for_functionality()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 全部测试完成！功能正常工作")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
