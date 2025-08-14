#!/usr/bin/env python3
"""
CampusLifeBench工具声明生成器
自动生成Agent可用的所有工具的JSON声明文件
"""

import json
import inspect
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# 添加项目路径
project_root = Path(__file__).parent
src_path = project_root / "LifelongAgentBench-main" / "src"
sys.path.insert(0, str(src_path))

try:
    from tasks.instance.campus_life_bench.environment import CampusEnvironment
    from tasks.instance.campus_life_bench.tools import ToolManager
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在正确的目录中运行此脚本，并且已安装所有依赖")
    sys.exit(1)


class ToolDeclarationGenerator:
    """工具声明生成器"""
    
    def __init__(self):
        self.environment = CampusEnvironment()
        self.tools = []
    
    def generate_all_tools(self) -> List[Dict[str, Any]]:
        """生成所有工具的声明"""
        print("正在扫描CampusEnvironment中的所有工具...")
        
        # 获取所有公共方法
        for attr_name in dir(self.environment):
            if not attr_name.startswith('_'):  # 排除私有方法
                attr = getattr(self.environment, attr_name)
                if callable(attr) and hasattr(attr, '__self__'):
                    try:
                        tool_info = self._extract_detailed_tool_info(attr)
                        self.tools.append(tool_info)
                        print(f"  ✅ 发现工具: {attr_name}")
                    except Exception as e:
                        print(f"  ⚠️  跳过 {attr_name}: {str(e)}")
        
        print(f"\n总共发现 {len(self.tools)} 个工具")
        return self.tools
    
    def _extract_detailed_tool_info(self, method) -> Dict[str, Any]:
        """提取详细的工具信息"""
        # 获取方法签名
        sig = inspect.signature(method)
        docstring = inspect.getdoc(method) or ""
        
        # 解析文档字符串
        description, param_descriptions = self._parse_docstring(docstring)
        
        # 构建参数信息
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':  # 跳过self参数
                continue
            
            param_type = self._get_param_type(param.annotation)
            param_desc = param_descriptions.get(param_name, f"Parameter {param_name}")
            
            parameters["properties"][param_name] = {
                "type": param_type,
                "description": param_desc
            }
            
            # 检查是否为必需参数
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)
        
        return {
            "name": method.__name__,
            "description": description or f"Tool: {method.__name__}",
            "parameters": parameters
        }
    
    def _parse_docstring(self, docstring: str) -> tuple:
        """解析文档字符串，提取描述和参数说明"""
        if not docstring:
            return "", {}
        
        lines = docstring.strip().split('\n')
        description = lines[0].strip() if lines else ""
        
        param_descriptions = {}
        in_args_section = False
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('args:'):
                in_args_section = True
                continue
            elif line.lower().startswith(('returns:', 'return:')):
                in_args_section = False
                continue
            
            if in_args_section and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    param_name = parts[0].strip()
                    param_desc = parts[1].strip()
                    param_descriptions[param_name] = param_desc
        
        return description, param_descriptions
    
    def _get_param_type(self, annotation) -> str:
        """将Python类型注解转换为JSON Schema类型"""
        if annotation == str or annotation == "str":
            return "string"
        elif annotation == int or annotation == "int":
            return "integer"
        elif annotation == bool or annotation == "bool":
            return "boolean"
        elif annotation == float or annotation == "float":
            return "number"
        elif annotation == dict or annotation == "dict":
            return "object"
        elif annotation == list or annotation == "list":
            return "array"
        elif hasattr(annotation, '__origin__'):
            if annotation.__origin__ is Union:
                # 处理Optional类型 (Union[T, None])
                args = annotation.__args__
                if len(args) == 2 and type(None) in args:
                    non_none_type = next(arg for arg in args if arg is not type(None))
                    return self._get_param_type(non_none_type)
        return "string"  # 默认为字符串类型
    
    def save_to_file(self, filename: str = "campus_life_bench_tools_complete.json"):
        """保存工具声明到文件"""
        tools_data = {
            "metadata": {
                "system": "CampusLifeBench",
                "version": "1.0",
                "total_tools": len(self.tools),
                "generated_by": "ToolDeclarationGenerator",
                "description": "Complete tool declarations for CampusLifeBench Agent"
            },
            "tools": self.tools
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tools_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n工具声明已保存到: {filename}")
        return filename
    
    def validate_tools(self) -> Dict[str, Any]:
        """验证工具声明的完整性"""
        validation_results = {
            "total_tools": len(self.tools),
            "tools_by_system": {},
            "missing_descriptions": [],
            "missing_parameters": [],
            "validation_passed": True
        }
        
        # 按系统分类工具
        system_mapping = {
            "email": ["send_email", "view_inbox", "reply_email", "delete_email"],
            "calendar": ["add_event", "remove_event", "update_event", "view_schedule", "query_advisor_availability"],
            "map": ["find_building_id", "get_building_details", "find_room_location", "find_optimal_path", 
                   "query_buildings_by_property", "get_building_complex_info", "list_valid_query_properties"],
            "geography": ["set_location", "walk_to", "get_current_location"],
            "reservation": ["query_availability", "make_booking"],
            "information": ["list_chapters", "list_sections", "list_articles", "view_article", 
                          "list_by_category", "query_by_identifier"],
            "course_selection": ["browse_courses", "add_course", "remove_course", "assign_pass", 
                               "view_draft", "submit_draft"]
        }
        
        tool_names = [tool["name"] for tool in self.tools]
        
        for system, expected_tools in system_mapping.items():
            found_tools = [name for name in expected_tools if name in tool_names]
            validation_results["tools_by_system"][system] = {
                "expected": len(expected_tools),
                "found": len(found_tools),
                "missing": [name for name in expected_tools if name not in tool_names]
            }
        
        # 检查描述和参数
        for tool in self.tools:
            if not tool.get("description") or tool["description"].startswith("Tool:"):
                validation_results["missing_descriptions"].append(tool["name"])
            
            if not tool.get("parameters", {}).get("properties"):
                validation_results["missing_parameters"].append(tool["name"])
        
        # 判断验证是否通过
        if (validation_results["missing_descriptions"] or 
            validation_results["missing_parameters"] or
            any(system_info["missing"] for system_info in validation_results["tools_by_system"].values())):
            validation_results["validation_passed"] = False
        
        return validation_results
    
    def print_validation_report(self, validation_results: Dict[str, Any]):
        """打印验证报告"""
        print("\n" + "="*60)
        print("工具声明验证报告")
        print("="*60)
        
        print(f"总工具数: {validation_results['total_tools']}")
        
        print("\n按系统分类:")
        for system, info in validation_results["tools_by_system"].items():
            status = "✅" if not info["missing"] else "⚠️"
            print(f"  {status} {system}: {info['found']}/{info['expected']} 个工具")
            if info["missing"]:
                print(f"    缺失: {', '.join(info['missing'])}")
        
        if validation_results["missing_descriptions"]:
            print(f"\n⚠️  缺少描述的工具: {', '.join(validation_results['missing_descriptions'])}")
        
        if validation_results["missing_parameters"]:
            print(f"\n⚠️  缺少参数的工具: {', '.join(validation_results['missing_parameters'])}")
        
        overall_status = "✅ 通过" if validation_results["validation_passed"] else "❌ 失败"
        print(f"\n总体验证状态: {overall_status}")


def main():
    """主函数"""
    print("CampusLifeBench工具声明生成器")
    print("="*50)
    
    try:
        # 创建生成器
        generator = ToolDeclarationGenerator()
        
        # 生成所有工具
        tools = generator.generate_all_tools()
        
        # 验证工具
        validation_results = generator.validate_tools()
        generator.print_validation_report(validation_results)
        
        # 保存到文件
        filename = generator.save_to_file()
        
        print(f"\n🎉 工具声明生成完成!")
        print(f"文件位置: {Path(filename).absolute()}")
        
    except Exception as e:
        print(f"\n❌ 生成过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
