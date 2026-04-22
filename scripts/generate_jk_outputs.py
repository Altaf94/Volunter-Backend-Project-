import re
from pathlib import Path

# Update this path if your static_data.dart moves
SRC = r"C:\Users\Junaid.mazhar\AppData\Local\Temp\f1bf74d3-2b59-465f-bf5d-b0660ffa1c13_static_data.dart.zip.c13\static_data.dart"

SQL_OUT = Path("jamatkhana_inserts.sql")
DART_OUT = Path("jamatkhana_all.dart")


def main() -> None:
    text = Path(SRC).read_text(encoding="utf-8", errors="ignore")

    start = text.find("static List<Map<String, dynamic>> jamatkhana = [")
    if start == -1:
        raise SystemExit("Could not find jamatkhana array in file.")
    end = text.find("];", start)
    if end == -1:
        raise SystemExit("Malformed jamatkhana array (missing terminator)")
    block = text[start:end]

    entry_re = re.compile(
        r"\{[^}]*?\"code\"\s*:\s*\"(?P<code>[^\"]+)\"\s*,[^}]*?\"localCouncilId\"\s*:\s*(?P<lcid>\d+)\s*,[^}]*?\"name\"\s*:\s*\"(?P<name>[^\"]*)\"[^}]*?\}",
        re.DOTALL | re.IGNORECASE,
    )

    rows = []
    for m in entry_re.finditer(block):
        code = m.group("code").strip()
        lcid_num = int(m.group("lcid"))
        name = m.group("name").replace("'", "''").strip()
        lc_id = f"LC{lcid_num:03d}"
        rows.append((code, lc_id, name))

    if not rows:
        raise SystemExit("No jamatkhana entries parsed.")

    # SQL output
    sql_lines = [
        'INSERT INTO "JamatKhana" ("Id", "Code", "Name", "LocalCouncilId") VALUES'
    ]
    values = []
    for code, lc_id, name in rows:
        values.append(f"('{code}','{code}','{name}','{lc_id}')")
    # Chunk values to keep line sizes reasonable
    chunked = []
    chunk = []
    for i, v in enumerate(values, 1):
        chunk.append(v)
        if i % 100 == 0:
            chunked.append(",\n".join(chunk))
            chunk = []
    if chunk:
        chunked.append(",\n".join(chunk))

    sql_full = []
    for i, group in enumerate(chunked):
        tail = ";\n" if i == len(chunked) - 1 else ";\n"
        # Each group gets its own INSERT to avoid extremely long single statements
        sql_full.append(sql_lines[0] + "\n" + group + "\nON CONFLICT (\"Id\") DO NOTHING" + tail)

    SQL_OUT.write_text("".join(sql_full), encoding="utf-8")

    # Dart output
    dart_items = []
    for code, lc_id, name in rows:
        safe_name = name.replace("\\", "\\\\").replace("\"", r'\"')
        dart_items.append(
            f'  {{"id": "{code}", "code": "{code}", "localCouncilId": "{lc_id}", "name": "{safe_name}"}},'
        )

    dart_text = (
        "static List<Map<String, dynamic>> jamatkhana = [\n" +
        "\n".join(dart_items) +
        "\n];\n"
    )
    DART_OUT.write_text(dart_text, encoding="utf-8")

    print(f"Wrote {len(rows)} rows to {SQL_OUT} and {DART_OUT}")


if __name__ == "__main__":
    main()


