// Verified implementation of the userdir query (reference solution).
include "../spec/UserdirSpec.dfy"

module App refines UserdirSpec {
  method Search(name: Sql.Data) returns (sql: string)
  {
    sql := Sql.Unparse(Intended(name));
  }
}
