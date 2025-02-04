# Prow commands with Pipelines-as-Code

## Overview

Pipelines As Code Prow let you trigger Tekton Pipelines based on GitHub comments replicating some of the prow commands functionality.

## Supported Commands

The following commands are supported:

| Command                 | Description                                                      |
|-------------------------|------------------------------------------------------------------|
| `/assign user1 user2`   | Assigns users for review to the PR                               |
| `/unassign user1 user2` | Removes assigned users                                           |
| `/label bug feature`    | Adds labels to the PR                                            |
| `/unlabel bug feature`  | Removes labels from the PR                                       |
| `/lgtm`                 | Approves the PR if at least 2 org members have commented `/lgtm` |
| `/help`                 | Shows this help message                                          |

## Usage

Below is an example usage of a PipelineRun to be placed in your `.tekton`
directory that will listen to the comments issued by a authorized user and use
our pipeline to execute the commands.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: prow-commands
  annotations:
    pipelinesascode.tekton.dev/pipeline: "https://raw.githubusercontent.com/openshift-pipelines/pipelines-as-code-prow/refs/heads/main/pipeline-prow.yaml"
    pipelinesascode.tekton.dev/on-comment: "^/(help|lgtm|(assign|unassign|label|unlabel)[ ].*)$"
    pipelinesascode.tekton.dev/max-keep-runs: "2"
spec:
  params:
    - name: trigger_comment
      value: |
        {{ trigger_comment }}
    - name: repo_owner
      value: "{{ repo_owner }}"
    - name: repo_name
      value: "{{ repo_name }}"
    - name: pull_request_number
      value: "{{ pull_request_number }}"
    - name: pull_request_sender
      value: "{{ sender }}"
    - name: git_auth_secret
      value: "{{ git_auth_secret }}"
  pipelineRef:
    name: prow-commands
```

### Without Pipelines-as-Code

You can use this Pipeline as well without Pipelines-as-Code from triggers for
example. You just need to pass the necessary parameters to the
`TriggerTemplate`.

(feel free to contribute to this README with an example for other users).

## Contributing

Feel free to submit pull requests or open issues to help improve the
project.

### Development

You will need to install [uv](https://github.com/astral-sh/uv)

This project use generated PipelineRun as described
[here](https://blog.chmouel.com/2020/07/28/tekton-yaml-templates-and-script-feature/),
you will need to edit the files in [code](./code) and run `make` to regenerate
the main PipelineRun.

Please install the pre-commit hooks by running `pre-commit install` to make sure
your commits include the necessary files.

## Copyright

[Apache-2.0](./LICENSE)
