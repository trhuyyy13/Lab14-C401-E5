from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))

from data import synthetic_gen as sg


def build_chunk_list_lines(chunks):
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        preview = " ".join(chunk["text"].split()[:18])
        line = "{:03d} | {} | {} | {}".format(idx, chunk["doc_id"], chunk.get("source", ""), preview)
        lines.append(line)
    return lines


def main():
    chunks = sg.load_and_chunk_real_data(
        repo / "data.txt",
    )
    out = repo / "data" / "chunk_list.txt"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = build_chunk_list_lines(chunks)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
