// The classic vulnerable implementation: string concatenation.
// It is expected to FAIL verification. `make demo` shows that the gate rejects it
// and, separately, that the exploit works against it when compiled without proof.
include "../spec/UserdirSpec.dfy"

module App refines UserdirSpec {
  method Search(name: Sql.Data) returns (sql: string)
  {
    sql := "SELECT \"name\", \"email\" FROM \"users\" WHERE (\"name\" = '" + name + "')";
  }
}
