from typing import Mapping, Any, Sequence

INSTRUCTION_SCRIPT_GENERATION_DEMONSTRATION_INFO_LIST: Sequence[Mapping[str, Any]] = [
    {
        "instruction": "Create a group called 'testgroup'.",
        "initialization_script": "",
        "ground_truth_script": "addgroup testgroup",
        "evaluation_script": "getent group testgroup > /dev/null 2>&1; if [ $? -eq 0 ]; then exit 0; else exit 1; fi",
        "skill_list": ["addgroup"],
    },
    {
        "instruction": "Create a group called 'testgroup' and add 'testuser' to it.",
        "initialization_script": "useradd -m testuser",
        "ground_truth_script": "addgroup testgroup && usermod -a -G testgroup testuser",
        "evaluation_script": "id -nG testuser | grep -qw testgroup && exit 0 || exit 1",
        "skill_list": ["usermod", "addgroup"],
    },
    {
        "instruction": "Create a group called 'testgroup', add 'testuser' to it, and make '/shared' accessible only to members of 'testgroup'.",
        "initialization_script": "useradd -m testuser && mkdir /shared && chmod 755 /shared",
        "ground_truth_script": "addgroup testgroup && usermod -a -G testgroup testuser && chgrp testgroup /shared && chmod 770 /shared",
        "evaluation_script": "stat -c '%G' /shared | grep -qw testgroup && id -nG testuser | grep -qw testgroup && exit 0 || exit 1",
        "skill_list": ["usermod", "addgroup", "chmod", "chgrp"],
    },
]
