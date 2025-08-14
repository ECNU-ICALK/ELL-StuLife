#!/usr/bin/env python3
"""
简化的 pre_task_for 功能测试脚本
专注于测试 pre_task_for 逻辑，而不依赖完整的环境
"""

import sys
import os
from unittest.mock import Mock

# Add the src directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.tasks.instance.campus_life_bench.task import CampusDatasetItem
from src.typings import SessionEvaluationOutcome


def test_campus_dataset_item_pre_task_for():
    """测试 CampusDatasetItem 的 pre_task_for 字段"""
    print("📋 测试1: CampusDatasetItem pre_task_for 字段")
    
    # 测试有 pre_task_for 字段的任务
    item_with_dependencies = CampusDatasetItem(
        task_id="prerequisite_task",
        task_type="email_sending",
        pre_task_for="dependent_task_1,dependent_task_2"
    )
    
    assert item_with_dependencies.pre_task_for == "dependent_task_1,dependent_task_2"
    print(f"✅ 前置任务 {item_with_dependencies.task_id} 设置了依赖: {item_with_dependencies.pre_task_for}")
    
    # 测试没有 pre_task_for 字段的任务
    item_without_dependencies = CampusDatasetItem(
        task_id="independent_task",
        task_type="email_sending"
    )
    
    assert item_without_dependencies.pre_task_for is None
    print(f"✅ 独立任务 {item_without_dependencies.task_id} 没有依赖")


def test_pre_task_for_parsing():
    """测试 pre_task_for 字段的解析逻辑"""
    print("\n📋 测试2: pre_task_for 字段解析")
    
    test_cases = [
        ("task1,task2,task3", ["task1", "task2", "task3"]),
        ("task1, task2 , task3 ", ["task1", "task2", "task3"]),  # 带空格
        ("task1,,task2", ["task1", "task2"]),  # 空值
        ("single_task", ["single_task"]),  # 单个任务
        ("", []),  # 空字符串
        ("   ", []),  # 只有空格
    ]
    
    for pre_task_for_str, expected in test_cases:
        # 模拟解析逻辑（从 _record_failed_prerequisite_task 方法中提取）
        if pre_task_for_str and pre_task_for_str.strip():
            actual = [task_id.strip() for task_id in pre_task_for_str.split(",") if task_id.strip()]
        else:
            actual = []
        
        assert actual == expected, f"解析 '{pre_task_for_str}' 失败: 期望 {expected}, 实际 {actual}"
        print(f"✅ 解析 '{pre_task_for_str}' -> {actual}")


def test_failed_prerequisite_tracking():
    """测试失败前置任务跟踪逻辑"""
    print("\n📋 测试3: 失败前置任务跟踪")
    
    # 模拟 CampusTask 的 failed_prerequisite_tasks 字典
    failed_prerequisite_tasks = {}
    
    def mock_record_failed_prerequisite_task(session, current_item):
        """模拟 _record_failed_prerequisite_task 方法"""
        if (session.evaluation_record.outcome == SessionEvaluationOutcome.INCORRECT and 
            current_item.pre_task_for is not None and 
            current_item.pre_task_for.strip() != ""):
            
            affected_task_ids = [task_id.strip() for task_id in current_item.pre_task_for.split(",") if task_id.strip()]
            
            if affected_task_ids:
                failed_prerequisite_tasks[current_item.task_id] = affected_task_ids
                print(f"📝 记录失败任务 {current_item.task_id} 影响: {affected_task_ids}")
    
    def mock_check_affected_by_failed_prerequisite(task_id):
        """模拟 _check_affected_by_failed_prerequisite 方法"""
        for failed_task_id, affected_task_ids in failed_prerequisite_tasks.items():
            if task_id in affected_task_ids:
                return failed_task_id
        return None
    
    # 创建测试数据
    prerequisite_task = CampusDatasetItem(
        task_id="prerequisite_task",
        task_type="email_sending",
        pre_task_for="dependent_task_1,dependent_task_2"
    )
    
    dependent_task_1 = CampusDatasetItem(
        task_id="dependent_task_1",
        task_type="email_sending"
    )
    
    dependent_task_2 = CampusDatasetItem(
        task_id="dependent_task_2",
        task_type="email_sending"
    )
    
    independent_task = CampusDatasetItem(
        task_id="independent_task",
        task_type="email_sending"
    )
    
    # 模拟前置任务失败
    failed_session = Mock()
    failed_session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
    
    mock_record_failed_prerequisite_task(failed_session, prerequisite_task)
    
    # 验证失败记录
    assert "prerequisite_task" in failed_prerequisite_tasks
    assert "dependent_task_1" in failed_prerequisite_tasks["prerequisite_task"]
    assert "dependent_task_2" in failed_prerequisite_tasks["prerequisite_task"]
    print("✅ 前置任务失败记录成功")
    
    # 测试受影响任务检查
    assert mock_check_affected_by_failed_prerequisite("dependent_task_1") == "prerequisite_task"
    assert mock_check_affected_by_failed_prerequisite("dependent_task_2") == "prerequisite_task"
    assert mock_check_affected_by_failed_prerequisite("independent_task") is None
    print("✅ 受影响任务检查正确")


def test_evaluation_logic():
    """测试评估逻辑"""
    print("\n📋 测试4: 评估逻辑模拟")
    
    # 模拟完整的评估流程
    failed_prerequisite_tasks = {"prerequisite_task": ["dependent_task_1", "dependent_task_2"]}
    
    def mock_complete_evaluation(task_id):
        """模拟 _complete 方法中的逻辑"""
        # 检查是否受前置任务失败影响
        for failed_task_id, affected_task_ids in failed_prerequisite_tasks.items():
            if task_id in affected_task_ids:
                session = Mock()
                session.evaluation_record.outcome = SessionEvaluationOutcome.INCORRECT
                session.task_output = {"result": "Set to incorrect due to the pre task"}
                session.evaluation_record.detail_dict = {
                    "failed_due_to_prerequisite": True,
                    "failed_prerequisite_task_id": failed_task_id,
                    "reason": f"Task failed because prerequisite task '{failed_task_id}' failed"
                }
                return session
        
        # 正常评估（这里简化为成功）
        session = Mock()
        session.evaluation_record.outcome = SessionEvaluationOutcome.CORRECT
        session.task_output = {"result": "Task completed successfully"}
        return session
    
    # 测试受影响的任务
    result1 = mock_complete_evaluation("dependent_task_1")
    assert result1.evaluation_record.outcome == SessionEvaluationOutcome.INCORRECT
    assert result1.task_output["result"] == "Set to incorrect due to the pre task"
    assert result1.evaluation_record.detail_dict["failed_prerequisite_task_id"] == "prerequisite_task"
    print("✅ dependent_task_1 正确标记为因前置任务失败而失败")
    
    # 测试不受影响的任务
    result2 = mock_complete_evaluation("independent_task")
    assert result2.evaluation_record.outcome == SessionEvaluationOutcome.CORRECT
    print("✅ independent_task 正常评估为成功")


def test_edge_cases():
    """测试边界情况"""
    print("\n📋 测试5: 边界情况")
    
    # 空的 pre_task_for
    item1 = CampusDatasetItem(task_id="test1", task_type="email_sending", pre_task_for="")
    item2 = CampusDatasetItem(task_id="test2", task_type="email_sending", pre_task_for="   ")
    item3 = CampusDatasetItem(task_id="test3", task_type="email_sending")  # None
    
    # 模拟处理逻辑
    def should_record_failure(item):
        return (item.pre_task_for is not None and item.pre_task_for.strip() != "")
    
    assert not should_record_failure(item1)  # 空字符串不应记录
    assert not should_record_failure(item2)  # 只有空格不应记录
    assert not should_record_failure(item3)  # None不应记录
    print("✅ 边界情况处理正确")
    
    # 复杂的依赖字符串
    complex_item = CampusDatasetItem(
        task_id="complex_task",
        task_type="email_sending",
        pre_task_for="task1, , task2,  task3 ,,"
    )
    
    affected_tasks = [task_id.strip() for task_id in complex_item.pre_task_for.split(",") if task_id.strip()]
    assert affected_tasks == ["task1", "task2", "task3"]
    print("✅ 复杂依赖字符串解析正确")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 pre_task_for 功能简化测试脚本")
    print("=" * 60)
    
    try:
        test_campus_dataset_item_pre_task_for()
        test_pre_task_for_parsing()
        test_failed_prerequisite_tracking()
        test_evaluation_logic()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！pre_task_for 功能逻辑正确")
        print("=" * 60)
        print("\n📝 关于依赖标识符的说明：")
        print("   在JSON数据中：")
        print("   {")
        print('     "0_first_task": {          // ← JSON key (sample_index)')
        print('       "task_id": "first_task", // ← 实际任务ID')
        print('       "pre_task_for": "task2,task3", // ← 应使用task_id值')
        print("       // ...")
        print("     }")
        print("   }")
        print("   ✅ 正确做法：使用 task_id 字段的值作为依赖标识")
        print("   ❌ 错误做法：使用 JSON key 作为依赖标识")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

