# Environment Migration Tasks

This document tracks the outstanding environment work that used to live as an informal TODO list in `metagpt/environment/README.md`. Each item now has concrete acceptance criteria so we can assign, scope, and verify the effort.

| Task | Summary | Acceptance Criteria | Notes |
| --- | --- | --- | --- |
| Android assistant demo | Restore the Android app-operation assistant under `examples/android_assistant` | • Example runs end-to-end against the current environment abstraction.<br>• README includes setup instructions and a happy-path transcript.<br>• Automated smoke test (or recorded session) lives alongside the example. | Depends on up-to-date device control mocks. |
| Werewolf migration | Port werewolf roles/actions from the legacy stack | • Roles compile without `FIXME` placeholders.<br>• Integration test covers a full round-trip (night + day cycle).<br>• Legacy assets removed or clearly marked deprecated. | Coordinate with `metagpt/ext/werewolf` owners. |
| Minecraft migration | Port Minecraft roles/actions from the legacy stack | • Agent can connect to target environment using the new API registry.<br>• Minimal scripted quest succeeds (move, gather, craft).<br>• Docs updated with launch instructions and known limitations. | Requires refreshed world templates. |
| Stanford Town migration | Finish migrating Stanford Town roles/actions | • Communication and memory flows work with current `Action` API.<br>• Story replay and reflection pipelines pass regression tests.<br>• Remaining `TODO`/`FIXME` comments in the module resolved or tracked elsewhere. | Relates to conversation automation work tracked in issue #? (link once created). |

> Tip: When you start one of these tasks, add an issue in GitHub and reference this table so the status remains transparent.
