/* Oracle built from SQLite's own source: exposes the real tokenizer and the real parse tree.
 *
 * This file is compiled together with the SQLite amalgamation (it #includes sqlite3.c) with
 * -DSQLITE_DEBUG -DSQLITE_ENABLE_TREETRACE, so it can call the tokenizer sqlite3GetToken() and
 * switch on SQLite's tree tracing, which prints the parse tree of each SELECT.
 *
 * Protocol (stdin, one request per line):  <mode> <hex-encoded UTF-8 SQL>
 *   T  tokenize:  prints "TOK <NAME> <length> <hex of token text>" per token, then "END"
 *   P  parse:     prepares the statement and prints SQLite's own tree dump, then "END"
 *   V  value:     evaluates "SELECT <sql>" and prints "VAL <hex of the text result>"
 *   X  exec:      runs a setup statement and prints "RC <code>"
 *   Q  query:     runs a SELECT and prints "ROW <hex col0> <hex col1>" per row, then "RC <code>"
 */
#include "sqlite3.c"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *tkname(int t) {
  switch (t) {
    case TK_SELECT: return "SELECT"; case TK_FROM: return "FROM"; case TK_WHERE: return "WHERE";
    case TK_ID: return "ID"; case TK_STRING: return "STRING"; case TK_INTEGER: return "INTEGER";
    case TK_FLOAT: return "FLOAT"; case TK_EQ: return "EQ"; case TK_NE: return "NE"; case TK_LT: return "LT";
    case TK_LE: return "LE"; case TK_GT: return "GT"; case TK_GE: return "GE"; case TK_AND: return "AND";
    case TK_OR: return "OR"; case TK_NOT: return "NOT"; case TK_LP: return "LP"; case TK_RP: return "RP";
    case TK_COMMA: return "COMMA"; case TK_SPACE: return "SPACE"; case TK_MINUS: return "MINUS";
    case TK_PLUS: return "PLUS"; case TK_SEMI: return "SEMI"; case TK_ILLEGAL: return "ILLEGAL";
    case TK_COMMENT: return "COMMENT"; case TK_VARIABLE: return "VARIABLE"; case TK_BLOB: return "BLOB";
    default: return "OTHER";
  }
}

static int unhex(const char *h, unsigned char **out) {
  size_t n = strlen(h) / 2;
  unsigned char *b = malloc(n + 1);
  for (size_t i = 0; i < n; i++) { unsigned v; sscanf(h + 2 * i, "%2x", &v); b[i] = (unsigned char)v; }
  b[n] = 0; *out = b; return (int)n;
}

static void tokenize(const unsigned char *z, int n) {
  int i = 0;
  while (i < n && z[i]) {
    int t = 0; i64 len = sqlite3GetToken(z + i, &t);
    printf("TOK %s %lld ", tkname(t), (long long)len);
    for (i64 k = 0; k < len; k++) printf("%02x", z[i + k]);
    printf("\n");
    if (len <= 0) break;
    i += (int)len;
  }
  if (i < n) printf("STOP at %d of %d (NUL or end)\n", i, n);
}

int main(void) {
  sqlite3 *db;
  sqlite3_open(":memory:", &db);
  sqlite3_db_config(db, SQLITE_DBCONFIG_DQS_DML, 0, 0);
  sqlite3_db_config(db, SQLITE_DBCONFIG_DQS_DDL, 0, 0);
  sqlite3_exec(db, "CREATE TABLE users(id INTEGER, name TEXT, email TEXT, secret TEXT);", 0, 0, 0);
  static char line[1 << 22];
  while (fgets(line, sizeof line, stdin)) {
    char mode = line[0]; char *h = line + 2; h[strcspn(h, "\r\n")] = 0;
    unsigned char *sql; int n = unhex(h, &sql);
    if (mode == 'T') tokenize(sql, n);
    else if (mode == 'P') {
      sqlite3_stmt *st = 0; sqlite3TreeTrace = 0x10001;
      int rc = sqlite3_prepare_v2(db, (const char *)sql, n, &st, 0);
      sqlite3TreeTrace = 0; fflush(stdout);
      printf("RC %d\n", rc); sqlite3_finalize(st);
    }
    else if (mode == 'X') {
      printf("RC %d\n", sqlite3_exec(db, (const char *)sql, 0, 0, 0));
    } else if (mode == 'V' || mode == 'Q') {
      sqlite3_stmt *st = 0; int rc;
      if (mode == 'V') {
        char *q = malloc(n + 8); memcpy(q, "SELECT ", 7); memcpy(q + 7, sql, n); q[n + 7] = 0;
        rc = sqlite3_prepare_v2(db, q, n + 7, &st, 0); free(q);
      } else rc = sqlite3_prepare_v2(db, (const char *)sql, n, &st, 0);
      if (rc != SQLITE_OK) printf("ERR %d\n", rc);
      else {
        int any = 0;
        while (sqlite3_step(st) == SQLITE_ROW) {
          any = 1; int nc = sqlite3_column_count(st);
          printf(mode == 'V' ? "VAL" : "ROW");
          for (int c = 0; c < nc; c++) {
            const unsigned char *t = sqlite3_column_text(st, c); int len = sqlite3_column_bytes(st, c);
            printf(" "); for (int k = 0; k < len; k++) printf("%02x", t[k]);
            if (len == 0) printf("-");
          }
          printf("\n");
        }
        if (mode == 'V' && !any) printf("NONE\n");
      }
      sqlite3_finalize(st);
    }
    printf("END\n"); fflush(stdout); free(sql);
  }
  return 0;
}
