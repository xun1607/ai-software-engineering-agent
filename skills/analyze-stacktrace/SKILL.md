---
name: analyze-stacktrace
description: Analyzes a Java exception stacktrace to pinpoint the exact source file, line number, and the variable most likely to be null.
version: 1.0.0
category: SoftwareEngineering/Debugging
level: atomic
tags: [java, stacktrace, debug, null-pointer]

input:
  type: object
  required: [stacktrace, source_path]
  properties:
    stacktrace:
      type: string
      description: Full Java exception stacktrace text
    source_path:
      type: string
      description: Root path of the Java source code

output:
  type: object
  properties:
    file:
      type: string
      description: Java source file where the error originated (e.g. UserService.java)
    line:
      type: integer
      description: Line number where the NullPointerException occurred
    variable:
      type: string
      description: The variable or object reference most likely to be null

constraints:
  host:
    os: [linux, darwin, windows]
  resources:
    memory: "512MB"
    timeout: "30s"
  safety:
    fs_access: read-only
    requires_approval: false
---

## Instructions

1. Parse the stacktrace line by line.
2. Find the FIRST stack frame that belongs to user project code — skip frames from `java.lang`, `sun.`, `org.springframework`, `com.sun`, `javax.`, hibernate, and other third-party libraries.
3. From that frame, extract: the class/file name and the line number.
4. Look at the exception message (e.g. "Cannot invoke ... because X is null") to identify the null variable. If no explicit message, infer from context.
5. Return file, line, and variable as JSON — nothing else.
