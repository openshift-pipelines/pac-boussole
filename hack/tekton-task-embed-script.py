#!/usr/bin/env python3
#
# Copyright 2025 Chmouel Boudjnah <chmouel@redhat.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Launch with uv run or install the dependency by other mean
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "ruamel.yaml",
# ]
# ///
import argparse
import io
import os.path
import re
import sys
import typing

from ruamel.yaml import YAML

REGEXP = r"^#include\s*([^$]*)"


def replace(args: argparse.Namespace) -> typing.List:
    yaml = YAML()
    with open(args.yaml_file, encoding="utf-8") as fp:
        docs = yaml.load_all(fp)
        rets = []
        for yamlDoc in docs:
            if "spec" not in yamlDoc and "tasks" not in yamlDoc["spec"]:
                continue

            if "tasks" in yamlDoc["spec"]:
                # TODO: handle multiple
                steps = yamlDoc["spec"]["tasks"][0]["taskSpec"]["steps"]
            else:
                print(f"ERROR: no steps found in task: {yamlDoc['metadata']['name']}")
                print(f"available keys: {list(yamlDoc['spec'].keys())}")
                return []

            if args.using_image:
                yamlDoc["spec"]["tasks"][0]["taskSpec"]["steps"][0]["image"] = (
                    args.using_image
                )
                del yamlDoc["spec"]["tasks"][0]["taskSpec"]["steps"][0]["script"]
            else:
                for task in steps:
                    if "script" not in task:
                        continue
                    if not task["script"].startswith("#include "):
                        continue
                    match = re.match(REGEXP, task["script"])
                    if not match:
                        continue
                    filename = match[1].strip()
                    rpath = os.path.join(
                        os.path.dirname(os.path.abspath(args.yaml_file)), filename
                    )
                    if os.path.exists(rpath):
                        filename = rpath
                    if not os.path.exists(filename):
                        sys.stderr.write(
                            f"WARNING: we could not find a file called: {filename} in task: {yamlDoc['metadata']['name']} step: {task['name']}"
                        )
                        continue
                    with open(filename, encoding="utf-8") as fp:
                        task["script"] = fp.read()
            output = io.StringIO()
            yaml.dump(yamlDoc, output)
            rets.append(output.getvalue())
    return rets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage your embedded Tekton script task externally"
    )
    parser.add_argument("--using-image", "-i", help="Using image to run the script")
    parser.add_argument("yaml_file", help="Yaml file to parse")
    return parser.parse_args()


def main() -> str:
    ret = []
    args = parse_args()
    replaced = replace(args)
    for doc in replaced:
        if not doc or not doc.strip():
            continue
        ret.append("---")
        ret.append(doc.strip())
    return "\n".join(ret)


if __name__ == "__main__":
    print(main())
