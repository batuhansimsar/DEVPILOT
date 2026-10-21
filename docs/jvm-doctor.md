# JVM build detection

`devpilot doctor` recognizes root-level Maven (`pom.xml`) and Gradle
(`build.gradle` or `build.gradle.kts`) projects as Java/Kotlin workspaces.
The suggested test commands are `mvn test` and `gradle test`, respectively.

Inspection only checks regular build manifest filenames. It does **not**
follow symlinked manifests, parse build scripts, run a Gradle wrapper, or
execute project code. Running detected tests still requires the user's
explicit `devpilot test --trust` opt-in.

When Maven and Gradle build files coexist, doctor reports
`jvm-build-conflict` rather than guessing a JVM test runner. In polyglot
projects, an already discovered test command is retained.
