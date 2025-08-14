#!/usr/bin/env python3
"""
Test OpenaiLanguageModel with DeepSeek API
"""

import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.language_models.instance.openai_language_model import OpenaiLanguageModel
from src.typings import ChatHistory, ChatHistoryItem, Role

def test_openai_language_model():
    """Test OpenaiLanguageModel with DeepSeek API"""
    
    try:
        print("🔍 Testing OpenaiLanguageModel with DeepSeek API...")
        
        # Initialize language model
        language_model = OpenaiLanguageModel(
            model_name="deepseek-chat",
            api_key="sk-d4226415d55d492fb913479f1a8b6b9c",
            base_url="https://api.deepseek.com",
            role_dict={"user": "user", "agent": "assistant"}
        )
        print("✅ Language model initialized")
        
        # Create test chat history
        chat_history = ChatHistory()
        chat_history.inject({"role": Role.USER, "content": "Hello, please respond with 'OpenaiLanguageModel test successful'"})

        print(f"🔍 Chat history created successfully")
        
        # Test inference
        inference_config = {
            "temperature": 0.1,
            "max_tokens": 100
        }
        
        result = language_model._inference(
            batch_chat_history=[chat_history],
            inference_config_dict=inference_config,
            system_prompt="You are a helpful assistant."
        )
        
        print(f"✅ Inference successful!")
        print(f"📝 Result: {result}")
        
        if len(result) > 0:
            print(f"📝 Generated content: {result[0].content}")
            return True
        else:
            print("❌ Empty result")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_openai_language_model()
