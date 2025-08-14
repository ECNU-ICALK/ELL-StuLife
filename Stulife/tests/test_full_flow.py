#!/usr/bin/env python3
"""
Test full agent-task flow
"""

import sys
import os
import json

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.language_models.instance.openai_language_model import OpenaiLanguageModel
from src.agents.instance.language_model_agent import LanguageModelAgent
from src.tasks.instance.campus_life_bench.task import CampusTask, CampusDatasetItem
from src.typings import Session, SampleStatus, SessionEvaluationRecord, SessionEvaluationOutcome, ChatHistory
from src.factories.chat_history_item.online.chat_history_item_factory import ChatHistoryItemFactory

def test_full_flow():
    """Test the complete agent-task interaction flow"""
    
    try:
        print("🔍 Testing full agent-task flow...")
        
        # Initialize language model
        language_model = OpenaiLanguageModel(
            model_name="deepseek-chat",
            api_key="sk-d4226415d55d492fb913479f1a8b6b9c",
            base_url="https://api.deepseek.com",
            role_dict={"user": "user", "agent": "assistant"}
        )
        print("✅ Language model initialized")
        
        # Initialize agent with empty system prompt (system prompt comes from chat history)
        agent = LanguageModelAgent(
            language_model=language_model,
            system_prompt="",  # Empty system prompt - will use chat history
            inference_config_dict={
                "temperature": 0.1,
                "max_tokens": 1000
            }
        )
        print("✅ Agent initialized")
        
        # Create chat history factory
        chat_history_path = "src/tasks/instance/campus_life_bench/data/chat_history.json"
        chat_history_factory = ChatHistoryItemFactory(chat_history_path)
        print("✅ Chat history factory created")
        
        # Initialize task
        task = CampusTask(
            chat_history_item_factory=chat_history_factory,
            max_round=10
        )
        print("✅ Task initialized")
        
        # Load a test task
        with open("src/tasks/instance/campus_life_bench/data/e2e_test_tasks.json", 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # Get first actual task (skip metadata)
        task_ids = [k for k in test_data.keys() if k != "metadata"]
        first_task_id = task_ids[0]
        dataset_item_dict = test_data[first_task_id]
        dataset_item = CampusDatasetItem.model_validate(dataset_item_dict)
        print(f"✅ Loaded test task: {first_task_id}")
        
        # Create session
        session = Session(
            sample_index=first_task_id,
            task_name="campus_life_bench",
            sample_status=SampleStatus.INITIAL,
            chat_history=ChatHistory(),
            evaluation_record=SessionEvaluationRecord(outcome=SessionEvaluationOutcome.UNSET)
        )
        print("✅ Session created")
        
        # Set dataset item in task
        task._Task__current_dataset_item = dataset_item
        task.current_sample_index = first_task_id
        
        # Reset task (this should inject system prompt and instruction)
        task._reset(session)
        print("✅ Task reset completed")
        
        # Check chat history
        try:
            # Check all items in chat history
            for i in range(3):  # Check first 3 items
                try:
                    item = session.chat_history.get_item_deep_copy(i)
                    print(f"📝 Chat item {i}: role={item.role}, content={item.content[:100]}...")
                except:
                    break

            last_item = session.chat_history.get_item_deep_copy(-1)
            print(f"📝 Last chat item role: {last_item.role}")
            print(f"📝 Last chat item content: {last_item.content[:100]}...")
        except Exception as e:
            print(f"❌ Failed to get chat history: {e}")
            return False
        
        # Test agent inference
        print("🔍 Testing agent inference...")
        agent.inference(session)
        
        # Get agent response
        agent_response = session.chat_history.get_item_deep_copy(-1).content
        print(f"✅ Agent response: {repr(agent_response)}")
        
        if agent_response.strip():
            print("✅ Agent generated non-empty response!")
            
            # Test parsing
            parsed_result = task._parse_agent_response(agent_response)
            print(f"📝 Parsed action: {parsed_result.action}")
            print(f"📝 Parsed content: {parsed_result.content}")
            
            return True
        else:
            print("❌ Agent generated empty response")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_full_flow()
