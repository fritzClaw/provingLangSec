// Approved specification of the userdir query. Frozen: changes require owner approval.
//
// Reading in plain English: whatever text Search returns is EXACTLY the SQL text
// that the SQL layer produces for the intended query tree. In that tree the
// untrusted name appears only as a string literal; the table and both columns
// are fixed. Because the SQL layer proves Parse(Unparse(t)) == Some(t), the
// database sees precisely that tree, whatever characters the name contains.

include "../../../lib/SqlProof.dfy"

abstract module UserdirSpec {
  import Sql
  import Prelude

  function Intended(name: Sql.Data): Sql.Query {
    Sql.Select(["name", "email"], "users",
               Prelude.Some(Sql.Cmp(Sql.Col("name"), Sql.Eq, Sql.Str(name))))
  }

  method Search(name: Sql.Data) returns (sql: string)
    ensures sql == Sql.Unparse(Intended(name))
}
