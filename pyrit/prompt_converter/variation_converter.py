import json
import logging
import pathlib

from pyrit.interfaces import ChatSupport
from pyrit.prompt_converter import PromptConverter
from pyrit.models import PromptTemplate, ChatMessage
from pyrit.common.path import DATASETS_PATH
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class VariationConverter(PromptConverter):
    def __init__(
        self, converter_target: ChatSupport, *, prompt_template: PromptTemplate = None, number_variations: int = 10
    ):
        self.converter_target = converter_target

        # set to default strategy if not provided
        prompt_template = (
            prompt_template
            if prompt_template
            else PromptTemplate.from_yaml_file(
                pathlib.Path(DATASETS_PATH) / "attack_strategies" / "prompt_variation" / "prompt_variation.yaml"
            )
        )

        if number_variations < 0 or number_variations > 1000:
            logger.log(logging.WARNING, "Number of variations should be between 0 and 1000. Defaulting to 10")
            number_variations = 10

        self.system_prompt = str(
            prompt_template.apply_custom_metaprompt_parameters(number_iterations=str(number_variations))
        )

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def convert(self, prompts: list[str]) -> list[str]:
        """
        Generates variations of the input prompts using the converter target.
        Parameters:
            prompts: list of prompts to convert
        Return:
            target_responses: list of prompt variations generated by the converter target
        """
        all_prompts = []
        for prompt in prompts:
            chat_entries = [
                ChatMessage(role="system", content=self.system_prompt),
                ChatMessage(role="user", content=prompt),
            ]

            response_msg = self.converter_target.complete_chat(messages=chat_entries)
            try:
                prompt_variations = json.loads(response_msg)
                for variation in prompt_variations:
                    all_prompts.append(variation)
            except json.JSONDecodeError:
                logger.warning(logging.WARNING, f"could not parse response as JSON {response_msg}")
        return all_prompts