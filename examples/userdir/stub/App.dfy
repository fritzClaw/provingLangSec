// Starting point of every `make agent` run: the agent replaces this file.
// It deliberately fails verification until the real implementation is written.
include "../spec/UserdirSpec.dfy"

module App refines UserdirSpec {
  method Search(name: Sql.Data) returns (sql: string)
  {
    sql := "";
  }
}
