import json
from typing import Callable, TypeVar

T = TypeVar("T")


class StandardDataFactoryUtility:
    @staticmethod
    def merge_data_dict(
        source_info_list: list[tuple[str, str]],
        output_dict_path: str,
        output_source_information_dict_path: str,
        get_entry_identifier_func: Callable[[T], str],
    ) -> None:
        merged_dict: dict[str, T] = {}
        source_info_output_dict: dict[str, str] = {}
        entry_identifier_to_source_info_dict: dict[str, str] = {}
        duplicated_source_information_list = []
        for source_identifier, data_dict_path in source_info_list:
            source_dict: dict[str, T] = json.load(open(data_dict_path, "r"))
            for key_in_data_dict, value in source_dict.items():
                source_info = f"{source_identifier}__{key_in_data_dict}"
                # region Check for duplicated entry
                if (
                    get_entry_identifier_func(value)
                    in entry_identifier_to_source_info_dict.keys()
                ):
                    duplicated_entry_source = entry_identifier_to_source_info_dict[
                        get_entry_identifier_func(value)
                    ]
                    duplicated_source_information_list.append(
                        f"{source_info}__#__{duplicated_entry_source}"
                    )
                    continue
                entry_identifier_to_source_info_dict[
                    get_entry_identifier_func(value)
                ] = source_info
                # endregion
                # region Merge and record source information
                key_in_merged_dict = str(len(merged_dict))
                merged_dict[key_in_merged_dict] = value
                source_info_output_dict[key_in_merged_dict] = source_info
                # endregion
        # region Record duplicated source information
        for i, duplicated_source_information in enumerate(
            duplicated_source_information_list
        ):
            source_info_output_dict[f"duplicated_pair_{i}"] = (
                duplicated_source_information
            )
        # endregion
        # region Dump result
        json.dump(merged_dict, open(output_dict_path, "w"), indent=2)  # noqa
        json.dump(
            source_info_output_dict,
            open(output_source_information_dict_path, "w"),  # noqa
            indent=2,
        )
        # endregion
