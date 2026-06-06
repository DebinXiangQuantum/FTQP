import Lake
open Lake DSL

package ftqp_formal where
  version := v!"0.1.0"

@[default_target]
lean_lib FTQP where
  srcDir := "."
