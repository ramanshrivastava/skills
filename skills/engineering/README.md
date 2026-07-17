# engineering

Skills for building software with teams of AI agents.

## Model-invoked skills

- **[milestone-orchestration](./milestone-orchestration/SKILL.md)** — Run a
  large, correctness-critical build (a port, rewrite, protocol/serializer, or
  migration) as a team of agents: a persistent coordinator that never writes bulk
  code dispatches one implementation agent per milestone, and every PR passes a
  merge gate whose adversarial half finds the bugs green tests miss. Worked
  example: the [rho](https://github.com/ramanshrivastava/rho) Rust port.
