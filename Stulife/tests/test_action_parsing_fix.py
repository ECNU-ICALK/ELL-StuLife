#!/usr/bin/env python3
"""
测试选课系统参数解析修复
验证<action>标签和括号课程ID的解析是否正确工作
"""

import unittest
import sys
import os
from pathlib import Path

# Add src directory to path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# Also add the project root for relative imports
sys.path.insert(0, str(project_root))

try:
    from src.tasks.instance.campus_life_bench.task import CampusTask
    from src.typings import Role, ChatHistoryItem, TaskName, SampleStatus
    from src.tasks.task import AgentAction
except ImportError as e:
    print(f"Import error: {e}")
    print("Available Python path:")
    for p in sys.path:
        print(f"  {p}")
    print("Make sure you're in the correct directory structure")
    sys.exit(1)


class TestActionParsingFix(unittest.TestCase):
    """测试Action解析修复"""
    
    def setUp(self):
        """设置测试环境"""
        pass
    
    def test_parse_course_id_with_parentheses_in_action_tags(self):
        """测试在<action>标签内包含括号的课程ID解析"""
        # 这是修复前失败的案例
        agent_response = '<action>Action: draft.add_course(section_id="GFJ003111100(2)")</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.EXECUTE)
        self.assertEqual(result.content, 'draft.add_course(section_id="GFJ003111100(2)")')
        print(f"✅ 成功解析带括号的课程ID: {result.content}")
    
    def test_parse_course_id_with_parentheses_without_action_tags(self):
        """测试不带<action>标签的向后兼容性"""
        # 向后兼容性测试
        agent_response = 'Action: draft.add_course(section_id="GFJ003111100(2)")'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.EXECUTE)
        self.assertEqual(result.content, 'draft.add_course(section_id="GFJ003111100(2)")')
        print(f"✅ 向后兼容性测试通过: {result.content}")
    
    def test_parse_multiple_parentheses_course_id(self):
        """测试包含多个括号的课程ID"""
        agent_response = '<action>Action: draft.add_course(section_id="COMPLEX(123)(ABC)(2)")</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.EXECUTE)
        self.assertEqual(result.content, 'draft.add_course(section_id="COMPLEX(123)(ABC)(2)")')
        print(f"✅ 多括号课程ID解析成功: {result.content}")
    
    def test_parse_regular_course_id(self):
        """测试普通课程ID（无括号）"""
        agent_response = '<action>Action: draft.add_course(section_id="CS101")</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.EXECUTE)
        self.assertEqual(result.content, 'draft.add_course(section_id="CS101")')
        print(f"✅ 普通课程ID解析成功: {result.content}")
    
    def test_parse_assign_pass_action(self):
        """测试assign_pass动作解析"""
        agent_response = '<action>Action: draft.assign_pass(section_id="GFJ003111100(2)", pass_type="A-Pass")</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.EXECUTE)
        self.assertEqual(result.content, 'draft.assign_pass(section_id="GFJ003111100(2)", pass_type="A-Pass")')
        print(f"✅ assign_pass动作解析成功: {result.content}")
    
    def test_parse_finish_action(self):
        """测试finish动作解析"""
        agent_response = '<action>Action: finish()</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.FINISH)
        self.assertIsNone(result.content)
        print("✅ finish()动作解析成功")
    
    def test_parse_quiz_answer(self):
        """测试Quiz答案解析"""
        agent_response = '<action>Answer: B</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.FINISH)
        self.assertEqual(result.content, 'Answer: B')
        self.assertEqual(result.finish_reason, 'quiz_answer')
        print("✅ Quiz答案解析成功")
    
    def test_parse_malformed_action_tags(self):
        """测试畸形<action>标签处理"""
        agent_response = 'Some text <action>Action: draft.add_course(section_id="GFJ003111100(2)")</action> more text'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.EXECUTE)
        self.assertEqual(result.content, 'draft.add_course(section_id="GFJ003111100(2)")')
        print(f"✅ 带干扰文本的action标签解析成功: {result.content}")
    
    def test_edge_case_nested_quotes(self):
        """测试嵌套引号的边界情况"""
        agent_response = '<action>Action: email.send_email(to="test@example.com", subject="Course: \\"GFJ003111100(2)\\"")</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.EXECUTE)
        # 验证包含转义引号和括号的参数能正确解析
        self.assertIn('GFJ003111100(2)', result.content)
        print(f"✅ 嵌套引号解析成功: {result.content}")
    
    def test_invalid_action_format(self):
        """测试无效的Action格式"""
        agent_response = '<action>Invalid action format</action>'
        
        result = CampusTask._parse_agent_response(agent_response)
        
        self.assertEqual(result.action, AgentAction.INVALID)
        print("✅ 无效Action格式正确识别")


def run_comprehensive_test():
    """运行全面的测试"""
    print("🚀 开始运行选课系统参数解析修复测试...")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestActionParsingFix)
    runner = unittest.TextTestRunner(verbosity=2)
    
    # 运行测试
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("🎉 所有测试通过！选课系统参数解析修复成功!")
        print(f"✅ 成功: {result.testsRun}个测试")
        return True
    else:
        print("❌ 测试失败!")
        print(f"❌ 失败: {len(result.failures)}个")
        print(f"❌ 错误: {len(result.errors)}个")
        
        # 打印失败详情
        for test, traceback in result.failures:
            print(f"\n失败测试: {test}")
            print(f"详情: {traceback}")
            
        for test, traceback in result.errors:
            print(f"\n错误测试: {test}")
            print(f"详情: {traceback}")
        
        return False


if __name__ == "__main__":
    # 运行测试
    success = run_comprehensive_test()
    
    # 根据测试结果设置退出码
    sys.exit(0 if success else 1)
