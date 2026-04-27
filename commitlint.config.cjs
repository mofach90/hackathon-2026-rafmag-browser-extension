// Commitlint config (CI validation of PR commits).
// See adr/0007-ci-cd-and-automation.md for why CI re-validates after pre-commit;
// see adr/0004-git-workflow.md for the type/scope vocabulary.

module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "feat",
        "fix",
        "docs",
        "refactor",
        "test",
        "chore",
        "perf",
        "style",
        "ci",
        "build",
        "revert",
      ],
    ],
    "scope-enum": [
      2,
      "always",
      ["extension", "backend", "scripts", "adr", "brainstorming", "experiments"],
    ],
    "scope-empty": [2, "never"],
    "header-max-length": [2, "always", 72],
    "subject-case": [2, "always", "lower-case"],
    "subject-empty": [2, "never"],
    "subject-full-stop": [2, "never", "."],
  },
};
