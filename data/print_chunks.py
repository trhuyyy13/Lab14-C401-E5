from pathlib import Path
import sys

repo = Path("c:/Users/dangv/Downloads/VinCourse/day14/Lab14-C401-E5")
sys.path.insert(0, str(repo))

from data import synthetic_gen as sg
chunks = sg.load_and_chunk_real_data(
    repo / "data" / "raw_repo",
    repo / "Nghị-định-Về-việc-ban-hành-Điều-lệ.txt",
)
out = repo / "data" / "chunk_list.txt"
out.parent.mkdir(parents=True, exist_ok=True)

lines = []
for idx, ch in enumerate(chunks, start=1):
    preview = " ".join(ch["text"].split()[:18])
    line = "{:03d} | {} | {} | {}".format(idx, ch["doc_id"], ch.get("source", ""), preview)
    lines.append(line)

out.write_text("\n".join(lines), encoding="utf-8")
print(out)
