import torch
import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from transformers import AutoTokenizer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.language_models.instance.huggingface_language_model import HuggingfaceLanguageModel
from src.typings import ChatHistory, ChatHistoryItem, Role, LanguageModelContextLimitException

class TestHuggingfaceLanguageModel(unittest.TestCase):

    def setUp(self):
        # Mock the model and tokenizer
        self.mock_model = MagicMock()
        self.mock_model.config.max_position_embeddings = 10
        self.mock_model.device = 'cpu'
        
        self.mock_tokenizer = MagicMock()
        self.mock_tokenizer.padding_side = "left"
        self.mock_tokenizer.pad_token = "[PAD]"
        self.mock_tokenizer.eos_token = "[EOS]"
        self.mock_tokenizer.eos_token_id = 1
        
        # Patch the AutoModelForCausalLM and AutoTokenizer to return our mocks
        self.patcher_model = patch('transformers.AutoModelForCausalLM.from_pretrained', return_value=self.mock_model)
        self.patcher_tokenizer = patch('transformers.AutoTokenizer.from_pretrained', return_value=self.mock_tokenizer)
        
        self.patcher_model.start()
        self.patcher_tokenizer.start()

        # Instantiate the language model
        self.language_model = HuggingfaceLanguageModel(
            model_name_or_path="test_model",
            role_dict={"user": "user", "agent": "assistant"}
        )
        self.language_model.model = self.mock_model
        self.language_model.tokenizer = self.mock_tokenizer

    def tearDown(self):
        self.patcher_model.stop()
        self.patcher_tokenizer.stop()

    def test_inference_truncates_long_input(self):
        # Given: an input that is longer than the model's max length
        long_input_ids = torch.tensor([[i for i in range(15)]])
        long_attention_mask = torch.ones_like(long_input_ids)
        
        self.mock_tokenizer.apply_chat_template.return_value = long_input_ids
        
        # The return value of _convert_message_list_to_model_input_dict is mocked
        with patch.object(self.language_model, '_convert_message_list_to_model_input_dict', return_value={
            "batch_input_ids": long_input_ids,
            "batch_attention_mask": long_attention_mask,
        }):
            # When: inference is called
            chat_history = ChatHistory([ChatHistoryItem(role=Role.USER, content="hello")])
            self.language_model.inference([chat_history])
        
            # Then: the input to the model's generate method should be truncated
            self.mock_model.generate.assert_called_once()
            call_args = self.mock_model.generate.call_args
            generated_input_ids = call_args[0][0]
            
            self.assertEqual(generated_input_ids.shape[-1], self.mock_model.config.max_position_embeddings)
            
            expected_truncated_ids = long_input_ids[:, -self.mock_model.config.max_position_embeddings:]
            self.assertTrue(torch.equal(generated_input_ids, expected_truncated_ids))

if __name__ == '__main__':
    unittest.main()
