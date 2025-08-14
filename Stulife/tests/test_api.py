#!/usr/bin/env python3
"""
Test DeepSeek API connection
"""

import requests
import json

def test_deepseek_api():
    """Test DeepSeek API directly"""
    
    api_key = "sk-d4226415d55d492fb913479f1a8b6b9c"
    base_url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Hello, please respond with 'API test successful'"}
        ],
        "temperature": 0.1,
        "max_tokens": 100
    }
    
    try:
        print("🔍 Testing DeepSeek API connection...")
        response = requests.post(base_url, headers=headers, json=data, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API Response: {json.dumps(result, indent=2)}")
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"✅ Generated Content: {content}")
                return True
            else:
                print("❌ No choices in response")
                return False
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"❌ Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_deepseek_api()
