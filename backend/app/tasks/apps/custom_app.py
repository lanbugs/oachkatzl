from __future__ import annotations

import json
import os


def build_command(task, workdir: str, custom_app) -> tuple[list[str], list[str]]:
    template = task.template
    script_path = os.path.join(workdir, template.playbook or "")

    # Start with the executable
    cmd = [custom_app.executable]

    # Apply default args
    try:
        default_args = json.loads(custom_app.default_args or "[]")
        cmd.extend(str(a) for a in default_args)
    except json.JSONDecodeError:
        pass

    # Template: {file} {arguments}
    args_tmpl = custom_app.args_template or "{file} {arguments}"
    try:
        template_args = json.loads(template.arguments or "[]")
    except json.JSONDecodeError:
        template_args = []

    try:
        override_args = json.loads(task.arguments_override or "[]")
    except json.JSONDecodeError:
        override_args = []

    effective_args = override_args if (template.allow_override_args and override_args) else template_args

    # Build the positional args according to the template
    if "{file}" in args_tmpl and "{arguments}" in args_tmpl:
        cmd.append(script_path)
        cmd.extend(str(a) for a in effective_args)
    elif "{file}" in args_tmpl:
        cmd.append(script_path)
    elif "{arguments}" in args_tmpl:
        cmd.extend(str(a) for a in effective_args)
    else:
        if script_path:
            cmd.append(script_path)
        cmd.extend(str(a) for a in effective_args)

    return cmd, []
