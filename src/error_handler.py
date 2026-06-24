import sys


def raise_error(file_path, file_data, message, pos):
    PADDING = 4
    lines = file_data.splitlines()
    line_idx = pos.line - 1
    col = pos.column - 1

    buf = []
    buf.append(f"Error: {message}")
    buf.append(f" --> {file_path}:{pos.line}:{pos.column}")
    buf.append("")

    if 0 <= line_idx < len(lines):
        context_before = 2
        context_after = 2
        start = max(0, line_idx - context_before)
        end = min(len(lines), line_idx + context_after + 1)

        for i in range(start, end):
            line_num = i + 1
            buf.append(f"{line_num:>{PADDING}} | {lines[i]}")

            if i == line_idx:
                indent = " " * (PADDING + 3)
                col_clamped = max(0, min(col, len(lines[i])))
                pointer = " " * col_clamped + "^"
                remaining = len(lines[i]) - col_clamped
                if remaining > 1:
                    pointer += "~" * min(remaining - 1, 5)
                buf.append(f"{indent}{pointer}")

    sys.stdout.write("\n".join(buf) + "\n")
    sys.exit(1)
