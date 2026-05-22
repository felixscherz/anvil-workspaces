# Anvil

```
█████╗ ███╗   ██╗██╗   ██╗██╗██╗     
██╔══██╗████╗  ██║██║   ██║██║██║     
███████║██╔██╗ ██║██║   ██║██║██║     
██╔══██║██║╚██╗██║╚██╗ ██╔╝██║██║     
██║  ██║██║ ╚████║ ╚████╔╝ ██║███████╗
╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═══╝  ╚═╝╚══════╝
```

Create isolated multi-repository workspaces for engineering tasks.

## Installation

```bash
uv tool install git+https://github.com/felixscherz/anvil
```

## Getting started

### Create a workspace

Provide a target directory and one or more repository specifiers. Each specifier can be a local path to an existing Git repository or any remote URL accepted by `git clone`.

```bash
anvil create --target /tmp/workspaces/feature-abc \
  ~/repos/my-service \
  git@github.com:org/other-service.git
```

Anvil will:

1. Infer the branch name from the target directory name (`feature-abc`).
2. For local paths — create a `git worktree` on a new branch at the tip of the default branch.
3. For remote URLs — clone the repository and check out a new branch.
4. Write a manifest to `/tmp/workspaces/feature-abc/.anvil/manifest.json`.

Example output:

```
Creating Anvil workspace: /tmp/workspaces/feature-abc
Branch: feature-abc
  + my-service -> /tmp/workspaces/feature-abc/my-service
  + other-service -> /tmp/workspaces/feature-abc/other-service

Created Anvil workspace: /tmp/workspaces/feature-abc
Branch: feature-abc
  - my-service -> /tmp/workspaces/feature-abc/my-service
  - other-service -> /tmp/workspaces/feature-abc/other-service
```

### Clean up a workspace

```bash
anvil clean --target /tmp/workspaces/feature-abc
```

Anvil reads the manifest, prints a summary, and prompts for confirmation before removing everything.

```
Anvil workspace: /tmp/workspaces/feature-abc
Branch: feature-abc
Repositories (2):
  - my-service (worktree) -> /tmp/workspaces/feature-abc/my-service
  - other-service (clone) -> /tmp/workspaces/feature-abc/other-service
Remove Anvil workspace at /tmp/workspaces/feature-abc containing 2 repositories? [y/N]
```

Skip the prompt with `--yes`:

```bash
anvil clean --target /tmp/workspaces/feature-abc --yes
```

## Notes

- The branch name is derived from the basename of `--target`. `/tmp/workspaces/feature-abc` → `feature-abc`.
- The same branch name is created in every repository in the workspace — this is expected and correct.
- If any repository fails during `create`, Anvil rolls back everything created in that run.
- Anvil will refuse to proceed if the target is non-empty, if a derived branch already exists, or if two repositories share the same derived name.
