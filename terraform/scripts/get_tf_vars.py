"""Fetches config and prints it as JSON for Terraform."""
import json
import os
import ast
import re


def get_pyproject_name(pyproject_path):
    """Reads the project name from pyproject.toml."""
    with open(pyproject_path) as f:
        content = f.read()
    match = re.search(r'^name\s*=\s*"(.*?)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find project name in pyproject.toml")
    return match.group(1)


def get_config_defaults(config_path):
    """Parses config.py to get default storage names as maps."""
    defaults = {
        "storage_queues": {},
        "storage_tables": {}
    }
    with open(config_path) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    if isinstance(node.value, ast.Call):
                        call = node.value
                        # Check for _get_setting call
                        if isinstance(call.func, ast.Name) and call.func.id == '_get_setting':
                            default_value = None
                            for keyword in call.keywords:
                                if keyword.arg == 'default' and isinstance(keyword.value, ast.Constant):
                                    default_value = keyword.value.value
                                    break
                            
                            if default_value:
                                if var_name.endswith("_QUEUE"):
                                    defaults["storage_queues"][var_name] = default_value
                                elif var_name.endswith("_TABLE"):
                                    defaults["storage_tables"][var_name] = default_value
    return defaults


def main():
    """Fetches config and prints it as JSON for Terraform."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # Go up two levels to get to the project root from terraform/scripts
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    
    pyproject_path = os.path.join(project_root, 'pyproject.toml')
    config_path = os.path.join(
        project_root, 'tvbingefriend_show_service', 'config.py'
    )

    package_name = get_pyproject_name(pyproject_path)
    
    # Shorten the package name
    short_package_name = package_name.replace(
        'tvbingefriend', 'tvbf'
    ).replace('service', 'svc')
    
    config_defaults = get_config_defaults(config_path)

    package_name_safe = re.sub(r'[^a-zA-Z0-9]', '', short_package_name).lower()
    package_name_db = short_package_name.replace('-', '_')

    # The values for storage resources must be JSON-encoded strings for Terraform
    output = {
        "package_name": short_package_name,
        "package_name_safe": package_name_safe,
        "package_name_db": package_name_db,
        "storage_queues": json.dumps(config_defaults["storage_queues"]),
        "storage_tables": json.dumps(config_defaults["storage_tables"]),
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
