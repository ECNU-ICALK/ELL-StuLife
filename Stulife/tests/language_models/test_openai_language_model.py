import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.language_models.instance.openai_language_model import OpenaiLanguageModel
from src.typings import ChatHistory, ChatHistoryItem, Role

class TestOpenaiLanguageModel(unittest.TestCase):

    def setUp(self):
        self.patcher_openai = patch('src.language_models.instance.openai_language_model.OpenAI')
        self.mock_openai_class = self.patcher_openai.start()
        self.mock_openai_instance = self.mock_openai_class.return_value
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="response"))]
        )

    def tearDown(self):
        self.patcher_openai.stop()

    def test_truncation_with_manual_max_tokens(self):
        # Given: A model with a manually set low max token count
        max_tokens = 50
        language_model = OpenaiLanguageModel(
            model_name="gpt-4",
            role_dict={"user": "user", "agent": "assistant"},
            maximum_prompt_token_count=max_tokens
        )

        # And: A chat history that will exceed the max token count
        # Each message is roughly 10-15 tokens
        chat_history = ChatHistory([
            ChatHistoryItem(role=Role.USER, content="This is the first long message to test truncation."),
            ChatHistoryItem(role=Role.AGENT, content="This is the first long response to test truncation."),
            ChatHistoryItem(role=Role.USER, content="This is the second long message that should be kept."),
            ChatHistoryItem(role=Role.AGENT, content="This is the second long response that should be kept."),
            ChatHistoryItem(role=Role.USER, content="This is the final message, definitely should be kept."),
        ])

        # When: inference is called
        language_model.inference([chat_history])
        
        # Then: the messages sent to the API should be truncated from the beginning
        self.mock_openai_instance.chat.completions.create.assert_called_once()
        call_args = self.mock_openai_instance.chat.completions.create.call_args
        sent_messages = call_args.kwargs['messages']
        
        # Check that the number of tokens is now under the limit
        sent_tokens = language_model._num_tokens_from_messages(sent_messages)
        self.assertLessEqual(sent_tokens, max_tokens)
        
        # Check that the earliest messages were removed
        contents = [msg['content'] for msg in sent_messages]
        self.assertNotIn("This is the first long message to test truncation.", contents)
        self.assertNotIn("This is the first long response to test truncation.", contents)
        
        # Check that the latest messages were kept
        self.assertIn("This is the final message, definitely should be kept.", contents)

    def test_truncation_with_system_prompt(self):
        # Given: A model with a low max token count and a system prompt
        max_tokens = 60
        system_prompt = "You are a helpful assistant."
        language_model = OpenaiLanguageModel(
            model_name="gpt-4",
            role_dict={"user": "user", "agent": "assistant"},
            maximum_prompt_token_count=max_tokens
        )
        
        chat_history = ChatHistory([
            ChatHistoryItem(role=Role.USER, content="This message should be removed."),
            ChatHistoryItem(role=Role.USER, content="This is the final message, definitely should be kept."),
        ])

        # When: inference is called with the system prompt
        language_model.inference([chat_history], system_prompt=system_prompt)
        
        # Then: the system prompt should be preserved, and the oldest user message should be removed
        self.mock_openai_instance.chat.completions.create.assert_called_once()
        call_args = self.mock_openai_instance.chat.completions.create.call_args
        sent_messages = call_args.kwargs['messages']
        
        self.assertEqual(sent_messages[0]['role'], 'system')
        self.assertEqual(sent_messages[0]['content'], system_prompt)
        
        contents = [msg['content'] for msg in sent_messages]
        self.assertNotIn("This message should be removed.", contents)
        self.assertIn("This is the final message, definitely should be kept.", contents)
        
        sent_tokens = language_model._num_tokens_from_messages(sent_messages)
        self.assertLessEqual(sent_tokens, max_tokens)


if __name__ == '__main__':
    unittest.main()
